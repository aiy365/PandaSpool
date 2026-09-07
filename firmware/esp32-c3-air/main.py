# PandaSpool 空气与机箱环境监测节点 (ESP32-C3)
# 传感器配置（独立总线方案）：
# - 仓内通道 (I2C1: SDA=8, SCL=9): ENS160 (0x53) + AHT20 (0x38)
# - 仓外通道 (I2C2: SDA=4, SCL=5): SHT4x/SHT3x (0x44)
# - 激光颗粒物 (UART1: RX=20, TX=21): 攀藤 PMS5003 (9600bps)
# - 人体微动雷达 (GPIO 10): 海凌科 LD2410C (OUT 高电平=有人)
import time, ujson, gc, machine, network
from machine import Pin, SoftI2C, UART

try:
    import urequests as rq
except ImportError:
    import requests as rq

import config

# 1. 硬件总线初始化
i2c_chamber = SoftI2C(sda=Pin(8, Pin.PULL_UP), scl=Pin(9, Pin.PULL_UP), freq=100000)
i2c_outside = SoftI2C(sda=Pin(4, Pin.PULL_UP), scl=Pin(5, Pin.PULL_UP), freq=100000)
pms_uart = UART(1, baudrate=9600, rx=Pin(20), tx=Pin(21))
ld_pin = Pin(10, Pin.IN, Pin.PULL_DOWN)

# 2. ENS160 初始化
def init_ens160():
    try:
        # 设置标准工作模式 (OPMODE = 0x02)
        i2c_chamber.writeto_mem(0x53, 0x10, b'\x02')
        time.sleep_ms(20)
        return True
    except Exception as e:
        print('ENS160 初始化失败:', e)
        return False

# 3. 读取仓外温湿度 (SHT4x / SHT3x 自适应)
def read_outside_th():
    # 优先尝试 SHT4x 命令 (0xFD)
    try:
        i2c_outside.writeto(0x44, b'\xfd')
        time.sleep_ms(15)
        d = i2c_outside.readfrom(0x44, 6)
        t = -45.0 + 175.0 * int.from_bytes(d[0:2], 'big') / 65535.0
        h = max(0.0, min(100.0, -6.0 + 125.0 * int.from_bytes(d[3:5], 'big') / 65535.0))
        return round(t, 1), round(h, 1)
    except Exception:
        pass

    # 回退尝试 SHT3x 命令 (0x2400)
    try:
        i2c_outside.writeto(0x44, b'\x24\x00')
        time.sleep_ms(20)
        d = i2c_outside.readfrom(0x44, 6)
        t = -45.0 + 175.0 * (d[0] << 8 | d[1]) / 65535.0
        h = max(0.0, min(100.0, 100.0 * (d[3] << 8 | d[4]) / 65535.0))
        return round(t, 1), round(h, 1)
    except Exception as e:
        print('仓外温湿度读取失败:', e)
        return None, None

# 4. 读取仓内温湿度 (AHT20)
def read_chamber_th():
    try:
        i2c_chamber.writeto(0x38, b'\xac\x33\x00')
        time.sleep_ms(80)
        d = i2c_chamber.readfrom(0x38, 7)
        h_raw = ((d[1] << 12) | (d[2] << 4) | (d[3] >> 4))
        t_raw = (((d[3] & 0x0F) << 16) | (d[4] << 8) | d[5])
        h = round((h_raw * 100.0) / 1048576.0, 1)
        t = round((t_raw * 200.0) / 1048576.0 - 50.0, 1)
        return t, h
    except Exception as e:
        print('仓内 AHT20 读取失败:', e)
        return None, None

# 5. 读取仓内空气质量 (ENS160) 并注入温湿度补偿
def read_ens160(t_comp=None, rh_comp=None):
    try:
        # 如果有 AHT20 温湿度，注入环境补偿
        if t_comp is not None and rh_comp is not None:
            t_raw = int((t_comp + 273.15) * 64)
            rh_raw = int(rh_comp * 512)
            i2c_chamber.writeto_mem(0x53, 0x13, t_raw.to_bytes(2, 'little'))
            i2c_chamber.writeto_mem(0x53, 0x15, rh_raw.to_bytes(2, 'little'))

        st = i2c_chamber.readfrom_mem(0x53, 0x20, 1)[0]
        aqi = i2c_chamber.readfrom_mem(0x53, 0x21, 1)[0]
        tvoc = int.from_bytes(i2c_chamber.readfrom_mem(0x53, 0x22, 2), 'little')
        eco2 = int.from_bytes(i2c_chamber.readfrom_mem(0x53, 0x24, 2), 'little')
        return tvoc, eco2, aqi
    except Exception as e:
        print('ENS160 读取失败:', e)
        return None, None, None

# 6. 读取 PMS5003 颗粒物
def read_pms5003(timeout_ms=3500):
    buf = b""
    end = time.ticks_add(time.ticks_ms(), timeout_ms)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        data = pms_uart.read()
        if data:
            buf += data
        while True:
            i = buf.find(b'\x42\x4d')
            if i < 0 or len(buf) - i < 32:
                buf = buf[i + 1:] if i >= 0 else buf[-31:]
                break
            f = buf[i:i + 32]
            if sum(f[0:30]) % 65536 == (f[30] << 8 | f[31]):
                pm1 = f[4] << 8 | f[5]
                pm25 = f[6] << 8 | f[7]
                pm10 = f[8] << 8 | f[9]
                return pm1, pm25, pm10
            buf = buf[i + 1:]
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
    print('PandaSpool 双通道机箱环境监测节点启动')
    print('========================================')
    init_ens160()
    ensure_wifi()

    fails = 0
    printing = False
    interval_s = 30  # 默认 30s 采样一次

    while True:
        try:
            # 读取各项传感器
            out_t, out_rh = read_outside_th()
            ch_t, ch_rh = read_chamber_th()
            tvoc, eco2, aqi = read_ens160(ch_t, ch_rh)
            pm1, pm25, pm10 = read_pms5003()
            presence = (ld_pin.value() == 1)

            payload = {
                'zone': config.ZONE if hasattr(config, 'ZONE') else 'room',
                'presence': presence
            }
            if out_t is not None: payload['t_c'] = out_t
            if out_rh is not None: payload['rh'] = out_rh
            if ch_t is not None: payload['chamber_t_c'] = ch_t
            if ch_rh is not None: payload['chamber_rh'] = ch_rh
            if tvoc is not None: payload['tvoc'] = tvoc
            if eco2 is not None: payload['eco2'] = eco2
            if aqi is not None: payload['aqi'] = aqi
            if pm25 is not None:
                payload['pm1'] = pm1
                payload['pm25'] = pm25
                payload['pm10'] = pm10

            print('【采集样本】', payload)

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

