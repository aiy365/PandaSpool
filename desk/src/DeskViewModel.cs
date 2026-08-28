using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;

namespace PrintPilotDesk;

public sealed class DeskViewModel : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;

    public string Badge { get; private set; } = "未配置";
    public Brush BadgeBrush { get; private set; } = BrushOf("#6B7280");
    public string JobLine { get; private set; } = "还没有机台数据";
    public string EtaLine { get; private set; } = "";
    public double Progress { get; private set; }
    public Visibility ProgressVisible { get; private set; } = Visibility.Collapsed;
    public string Nozzle { get; private set; } = "—";
    public string Bed { get; private set; } = "—";
    public string Layer { get; private set; } = "—";
    public string Remain { get; private set; } = "—";
    public string Pm25 { get; private set; } = "—";
    public string Climate { get; private set; } = "—";
    public string Presence { get; private set; } = "—";
    public string Boost { get; private set; } = "";
    public string AirNote { get; private set; } = "";
    public Visibility BoostVisible { get; private set; } = Visibility.Collapsed;
    public Visibility AirNoteVisible { get; private set; } = Visibility.Collapsed;
    public string Footer { get; private set; } = "左键打开机台页";
    public string Tip { get; private set; } = "PrintPilot";
    public bool Printing { get; private set; }
    public bool Offline { get; private set; } = true;

    public void Apply(DeskSnapshot d)
    {
        Offline = d.Offline;
        Printing = !d.Offline && d.Printing;
        Progress = Math.Clamp(d.Progress, 0, 100);
        ProgressVisible = Printing ? Visibility.Visible : Visibility.Collapsed;

        if (d.FetchError != "")
        {
            Badge = "离线";
            BadgeBrush = BrushOf("#6B7280");
            JobLine = d.FetchError;
            EtaLine = "";
            Footer = "左键打开设置，检查网址和令牌";
            Tip = "PrintPilot · " + d.FetchError;
        }
        else if (!d.Connected)
        {
            Badge = "未连拓竹";
            BadgeBrush = BrushOf("#F59E0B");
            JobLine = "Hub 在线，打印机 MQTT 未连";
            EtaLine = "";
            Footer = "去网站设置页看拓竹登录";
            Tip = "PrintPilot · 未连拓竹";
        }
        else if (d.Printing)
        {
            Badge = $"打印中  {Progress:0}%";
            BadgeBrush = BrushOf("#14B8A6");
            var job = DeskSnapshot.Fmt(d.Job);
            JobLine = job == "—" ? "正在打印" : job;
            EtaLine = string.IsNullOrWhiteSpace(d.Eta) ? "" : "大约 " + d.Eta + " 完成";
            Footer = "左键打开机台页";
            Tip = string.IsNullOrWhiteSpace(d.Eta)
                ? $"打印中 {Progress:0}%"
                : $"打印中 {Progress:0}% · {d.Eta}";
        }
        else
        {
            var st = string.IsNullOrWhiteSpace(d.GcodeState) ? d.Stage : d.GcodeState;
            Badge = string.IsNullOrWhiteSpace(st) ? "空闲" : st;
            BadgeBrush = BrushOf("#22C55E");
            JobLine = "打印机空闲";
            EtaLine = "";
            Footer = "左键打开机台页";
            Tip = "PrintPilot · 空闲";
        }

        Nozzle = DeskSnapshot.Fmt(d.NozzleTemp) + " / " + DeskSnapshot.Fmt(d.NozzleTarget);
        Bed = DeskSnapshot.Fmt(d.BedTemp) + " / " + DeskSnapshot.Fmt(d.BedTarget);
        Layer = DeskSnapshot.Fmt(d.Layer) + " / " + DeskSnapshot.Fmt(d.TotalLayer);
        Remain = d.RemainingMin > 0 ? d.RemainingMin.ToString("0") + " 分" : "—";
        Pm25 = DeskSnapshot.Fmt(d.Pm25);
        var t = DeskSnapshot.Fmt(d.TempC);
        var rh = DeskSnapshot.Fmt(d.Rh);
        Climate = (t == "—" && rh == "—") ? "—" : t + " ℃  ·  " + rh + " %";
        Presence = DeskSnapshot.Fmt(d.Presence);
        var boostOn = DeskSnapshot.Fmt(d.PrintBoostActive) is "是" or "true" or "True";
        Boost = boostOn ? "打印加强开着" : "";
        BoostVisible = boostOn ? Visibility.Visible : Visibility.Collapsed;
        AirNote = AirAge(d.AirTs);
        AirNoteVisible = AirNote.Length > 0 ? Visibility.Visible : Visibility.Collapsed;
        RaiseAll();
    }

    static string AirAge(JsonElement el)
    {
        long n = 0;
        if (el.ValueKind == JsonValueKind.Number)
            n = el.TryGetInt64(out var i) ? i : (long)el.GetDouble();
        else if (el.ValueKind == JsonValueKind.String && long.TryParse(el.GetString(), out var s))
            n = s;
        if (n <= 0)
            return "";
        if (n > 1_000_000_000_000)
            n /= 1000;
        var age = DateTimeOffset.Now.ToUnixTimeSeconds() - n;
        if (age < 15 * 60)
            return "";
        if (age < 3600)
            return $"探头已 {(age / 60):0} 分钟没报";
        return $"探头已 {(age / 3600):0} 小时没报";
    }

    void RaiseAll()
    {
        foreach (var p in new[]
        {
            nameof(Badge), nameof(BadgeBrush), nameof(JobLine), nameof(EtaLine),
            nameof(Progress), nameof(ProgressVisible), nameof(Nozzle), nameof(Bed),
            nameof(Layer), nameof(Remain), nameof(Pm25), nameof(Climate),
            nameof(Presence), nameof(Boost), nameof(AirNote), nameof(BoostVisible),
            nameof(AirNoteVisible), nameof(Footer), nameof(Tip), nameof(Printing), nameof(Offline),
        })
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(p));
    }

    static SolidColorBrush BrushOf(string hex)
    {
        var b = (SolidColorBrush)new BrushConverter().ConvertFromString(hex)!;
        b.Freeze();
        return b;
    }

    void On([CallerMemberName] string? n = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
}
