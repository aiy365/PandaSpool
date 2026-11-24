# PandaSpool 空气与机箱环境监测节点 (ESP32-C3)
# 固件版本: v2.4.0-sht-authority (2026-10-04)
# 传感器配置与权威分工：
# - SHT4x/SHT3x (0x44): 绝对温湿度权威（零自热，无热岛偏差）
#     - 仓外 (I2C2: SDA=4, SCL=5): 权威室温/室湿 (t_c, rh)
#     - 仓内 (I2C1: SDA=8, SCL=9): 权威仓温/仓湿 (chamber_t_c, chamber_rh，加装即自适应激活)
# - ENS160 (0x53) + AHT20 (0x38): 挥发物与气相监测
#     - AHT20 数据仅在内存中就地为同板 ENS160 提供精确温湿补偿，不对外暴露，彻底消除热岛虚高
#     - 通道 1 (I2C1: SDA=8, SCL=9): 仓内耗材释放 (tvoc, eco2, aqi)
#     - 通道 2 (I2C3 对照组: SDA=6, SCL=7): 仓外/对照组释放 (tvoc2, eco2_2, aqi2)
# - 激光颗粒物 (UART1: RX=20, TX=21): 攀藤 PMS5003 (9600bps，仓外)
# - 人体微动雷达 (GPIO 10): 海凌科 LD2410C (OUT 高电平=有人，仓外)

import time, ujson, gc, machine, network
from machine import Pin, SoftI2C, UART

try:
    import urequests as rq
except ImportError:
    import requests as rq

import config

# 1. 硬件总线初始化
i2c_chamber = SoftI2C(sda=Pin(8, Pin.PULL_UP), scl=Pin(9, Pin.PULL_UP), freq=100000)
i2c_chamber2 = SoftI2C(sda=Pin(6, Pin.PULL_UP), scl=Pin(7, Pin.PULL_UP), freq=100000)
i2c_outside = SoftI2C(sda=Pin(4, Pin.PULL_UP), scl=Pin(5, Pin.PULL_UP), freq=100000)
pms_uart = UART(1, baudrate=9600, rx=Pin(20), tx=Pin(21), rxbuf=512)
ld_pin = Pin(10, Pin.IN, Pin.PULL_DOWN)

# 2. ENS160 初始化
def init_ens160(bus, label="通道1"):
    try:
        bus.writeto_mem(0x53, 0x10, b'\x02') # 标准测量模式
        time.sleep_ms(20)
        return True
    except Exception:
        return False

# 3. 读取 SHT4x / SHT3x 温湿度通用函数 (权威测温，自适应总线)
def read_sht_bus(bus):
    # 优先尝试 SHT4x 命令 (0xFD)
    try:
        bus.writeto(0x44, b'\xfd')
        time.sleep_ms(15)
        d = bus.readfrom(0x44, 6)
        t = -45.0 + 175.0 * int.from_bytes(d[0:2], 'big') / 65535.0
        h = max(0.0, min(100.0, -6.0 + 125.0 * int.from_bytes(d[3:5], 'big') / 65535.0))
        return round(t, 1), round(h, 1)
    except Exception:
        pass

    # 回退尝试 SHT3x 命令 (0x2400)
    try:
        bus.writeto(0x44, b'\x24\x00')
        time.sleep_ms(20)
        d = bus.readfrom(0x44, 6)
        t = -45.0 + 175.0 * (d[0] << 8 | d[1]) / 65535.0
        h = max(0.0, min(100.0, 100.0 * (d[3] << 8 | d[4]) / 65535.0))
        return round(t, 1), round(h, 1)
    except Exception:
        return None, None

# 4. 读取 AHT20 温湿度通用函数（仅用于板载局部补偿，不对外显）
def read_aht20_bus(bus, label="通道1"):
    try:
        bus.writeto(0x38, b'\xac\x33\x00')
        time.sleep_ms(80)
        d = bus.readfrom(0x38, 7)
        h_raw = ((d[1] << 12) | (d[2] << 4) | (d[3] >> 4))
        t_raw = (((d[3] & 0x0F) << 16) | (d[4] << 8) | d[5])
        h = round((h_raw * 100.0) / 1048576.0, 1)
        t = round((t_raw * 200.0) / 1048576.0 - 50.0, 1)
        return t, h
    except Exception:
        return None, None

# 5. 读取 ENS160 挥发物通用函数 (注入 AHT20 温湿补偿)
def read_ens160_bus(bus, t_comp=None, rh_comp=None):
    try:
        if t_comp is not None and rh_comp is not None:
            t_raw = int((t_comp + 273.15) * 64)
            rh_raw = int(rh_comp * 512)
            bus.writeto_mem(0x53, 0x13, t_raw.to_bytes(2, 'little'))
            bus.writeto_mem(0x53, 0x15, rh_raw.to_bytes(2, 'little'))

        st = bus.readfrom_mem(0x53, 0x20, 1)[0]
        aqi = bus.readfrom_mem(0x53, 0x21, 1)[0]
        tvoc = int.from_bytes(bus.readfrom_mem(0x53, 0x22, 2), 'little')
        eco2 = int.from_bytes(bus.readfrom_mem(0x53, 0x24, 2), 'little')
        return tvoc, eco2, aqi
    except Exception:
        return None, None, None

# 6. 读取 PMS5003 颗粒物 (无损帧缓冲区解析)
def read_pms5003(timeout_ms=3500):
    buf = bytearray()
    end = time.ticks_add(time.ticks_ms(), timeout_ms)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        data = pms_uart.read()
        if data:
            buf.extend(data)
            if len(buf) > 256:
                buf = buf[-128:]
        while len(buf) >= 32:
            idx = buf.find(b'\x42\x4d')
            if idx == -1:
                buf = buf[-1:]
                break
            if idx > 0:
                buf = buf[idx:]
            if len(buf) < 32:
                break
            f = buf[:32]
            csum = (f[30] << 8) | f[31]
            if sum(f[0:30]) % 65536 == csum:
                pm1 = (f[4] << 8) | f[5]
                pm25 = (f[6] << 8) | f[7]
                pm10 = (f[8] << 8) | f[9]
                return pm1, pm25, pm10
            else:
                buf = buf[1:]
        time.sleep_ms(50)
    return None, None, None

# 7. WiFi 连接
wlan = None
def ensure_wifi():
    global wlan
    if wlan and wlan.isconnected():
        return True
    print('正在连接 WiFi:', config.WIFI_SSID)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
    for _ in range(25):
        time.sleep(1)
        if wlan.isconnected():
            print('WiFi 已连接，IP:', wlan.ifconfig()[0])
            return True
    print('WiFi 连接超时')
    return False

# 8. HTTP 上报
def report_to_hub(payload):
    gc.collect()
    url = config.SERVER + '/api/ingest/air'
    headers = {
        'Authorization': 'Bearer ' + config.AIR_TOKEN,
        'Content-Type': 'application/json'
    }
    r = rq.post(url, headers=headers, data=ujson.dumps(payload))
    code = r.status_code
    text = r.text
    r.close()
    return code, text

# 9. 主循环
def main():
    print('========================================')
    print('PandaSpool 空气节点 (v2.4.0-sht-authority)')
    print('========================================')
    init_ens160(i2c_chamber, "通道1(IO8/9)")
    init_ens160(i2c_chamber2, "通道2(IO6/7)")
    ensure_wifi()

    fails = 0
    printing = False
    interval_s = 30  # 默认 30s 采样一次

    while True:
        try:
            # 1. 权威环境温湿度（仅由 SHT 芯片测定）
            out_t, out_rh = read_sht_bus(i2c_outside)
            ch_sht_t, ch_sht_rh = read_sht_bus(i2c_chamber)   # 仓内 SHT（未加装时自动为 None）
            ch2_sht_t, ch2_sht_rh = read_sht_bus(i2c_chamber2) # 通道2 SHT（未加装时自动为 None）

            # 2. AHT20 纯幕后采样（仅就地喂给同板 ENS160 消除热岛，绝不暴露至 payload）
            ch_aht_t, ch_aht_rh = read_aht20_bus(i2c_chamber, "通道1(IO8/9)")
            tvoc, eco2, aqi = read_ens160_bus(i2c_chamber, ch_aht_t, ch_aht_rh)

            ch2_aht_t, ch2_aht_rh = read_aht20_bus(i2c_chamber2, "通道2(IO6/7)")
            tvoc2, eco2_2, aqi2 = read_ens160_bus(i2c_chamber2, ch2_aht_t, ch2_aht_rh)

            # 3. 颗粒物与雷达
            pm1, pm25, pm10 = read_pms5003()
            presence = (ld_pin.value() == 1)

            payload = {
                'zone': config.ZONE if hasattr(config, 'ZONE') else 'room',
                'presence': presence
            }
            # 权威室温/室湿
            if out_t is not None: payload['t_c'] = out_t
            if out_rh is not None: payload['rh'] = out_rh

            # 权威仓温/仓湿（只有硬件检测到独立的 SHT 芯片时才上报，彻底剔除 AHT20 自热偏差）
            if ch_sht_t is not None: payload['chamber_t_c'] = ch_sht_t
            if ch_sht_rh is not None: payload['chamber_rh'] = ch_sht_rh

            # 仓内 TVOC/eCO2/AQI
            if tvoc is not None: payload['tvoc'] = tvoc
            if eco2 is not None: payload['eco2'] = eco2
            if aqi is not None: payload['aqi'] = aqi

            # 颗粒物
            if pm25 is not None:
                payload['pm1'] = pm1
                payload['pm25'] = pm25
                payload['pm10'] = pm10

            # 对照组通道动态注入（如有）
            if ch2_sht_t is not None: payload['chamber2_t_c'] = ch2_sht_t
            if ch2_sht_rh is not None: payload['chamber2_rh'] = ch2_sht_rh
            if tvoc2 is not None: payload['tvoc2'] = tvoc2
            if eco2_2 is not None: payload['eco2_2'] = eco2_2
            if aqi2 is not None: payload['aqi2'] = aqi2

            print('【采集样本】', payload)
            if ch_aht_t is not None:
                print('  ↳ [AHT20幕后补偿] 局部板温=%.1f℃, 板湿=%.1f%% (仅用于ENS160算法)' % (ch_aht_t, ch_aht_rh or 0.0))

            if ensure_wifi():
                code, resp = report_to_hub(payload)
                print('上报状态: HTTP', code, '响应:', resp)
                if code == 200:
                    fails = 0
                    try:
                        resp_json = ujson.loads(resp)
                        printing = bool(resp_json.get('printing', False))
                    except Exception:
                        pass
                else:
                    fails += 1
            else:
                fails += 1

            # 动态间隔：打印中 30 秒高频采集材料挥发；空闲时 60 秒平稳采集
            interval_s = 30 if printing else 60

        except Exception as ex:
            print('主循环异常:', ex)
            fails += 1

        if fails >= 15:
            print('连续失败超限，系统重启中...')
            time.sleep(2)
            machine.reset()

        time.sleep(interval_s)

main()
