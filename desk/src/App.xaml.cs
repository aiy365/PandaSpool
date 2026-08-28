using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Threading;
using H.NotifyIcon;
using H.NotifyIcon.Core;

namespace PrintPilotDesk;

public partial class App : Application
{
    const string PingName = @"Local\PrintPilotDesk.bstccc.ping";

    Mutex? _mutex;
    EventWaitHandle? _ping;
    CancellationTokenSource? _pingCts;
    TaskbarIcon? _tray;
    DispatcherTimer? _timer;
    DispatcherTimer? _hoverDelay;
    DispatcherTimer? _leaveTimer;
    SettingsWindow? _settings;
    HoverCard? _hover;
    Window? _anchor;
    int _busy;
    bool _menuOpen;
    bool? _wasPrinting;
    string _iconSig = "";
    int _failStreak;
    NativePoint _hoverAt;

    public AppConfig Config { get; private set; } = new();
    public DeskViewModel Model { get; } = new();

    async void OnStartup(object sender, StartupEventArgs e)
    {
        DispatcherUnhandledException += (_, args) =>
        {
            Log("ui", args.Exception);
            args.Handled = true;
        };
        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
            Log("crash", args.ExceptionObject as Exception);
        TaskScheduler.UnobservedTaskException += (_, args) =>
        {
            Log("task", args.Exception);
            args.SetObserved();
        };
        TrimLog();

        _mutex = new Mutex(false, @"Local\PrintPilotDesk.bstccc");
        var created = false;
        try
        {
            created = _mutex.WaitOne(0);
        }
        catch (AbandonedMutexException)
        {
            created = true;
        }
        if (!created)
        {
            try
            {
                using var ping = EventWaitHandle.OpenExisting(PingName);
                ping.Set();
            }
            catch { /* first instance may be old */ }
            MessageBox.Show("PrintPilot 已经在托盘里。看任务栏右边。", "PrintPilot Desk");
            _mutex.Dispose();
            _mutex = null;
            Shutdown();
            return;
        }

        try
        {
            _ping = new EventWaitHandle(false, EventResetMode.AutoReset, PingName);
            _pingCts = new CancellationTokenSource();
            _ = Task.Run(() => ListenPing(_pingCts.Token));

            Config = AppConfig.Load();
            if (AutoStart.IsEnabled())
            {
                try { AutoStart.Set(true); }
                catch { /* 开机项还在，路径刷新失败就算了 */ }
            }
            _hover = new HoverCard { DataContext = Model };
            _hover.MouseLeftButtonUp += (_, _) => OpenMachineSite();
            _anchor = CreateAnchor();

            _tray = new TaskbarIcon
            {
                ToolTipText = "",
                TrayPopup = _hover,
                NoLeftClickDelay = true,
                MenuActivation = PopupActivationMode.None,
                PopupActivation = PopupActivationMode.None,
                ContextMenu = BuildMenu(),
                Icon = TrayIconFactory.Create(Model),
            };
            _tray.TrayLeftMouseUp += (_, _) =>
            {
                if (!Config.Ready)
                    OpenSettings();
                else
                    OpenMachineSite();
            };
            _tray.TrayRightMouseDown += (_, _) => SuppressHoverForMenu();
            _tray.TrayRightMouseUp += (_, _) => ShowTrayMenu();
            _tray.TrayKeyboardContextMenu += (_, _) => ShowTrayMenu();
            _tray.PreviewTrayContextMenuOpen += (_, ev) =>
            {
                ev.Handled = true;
                SuppressHoverForMenu();
            };
            _hoverDelay = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(220) };
            _hoverDelay.Tick += (_, _) =>
            {
                _hoverDelay.Stop();
                ShowHover();
            };
            _leaveTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(280) };
            _leaveTimer.Tick += (_, _) => MaybeCloseHover();
            _tray.TrayMouseMove += (_, _) => QueueHover();
            _tray.PreviewTrayToolTipOpen += (_, ev) =>
            {
                ev.Handled = true;
                QueueHover();
            };
            _tray.ForceCreate(enablesEfficiencyMode: false);

            _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(Math.Max(5, Config.PollSeconds)) };
            _timer.Tick += async (_, _) => await RefreshAsync();
            _timer.Start();

            await RefreshAsync();
            if (!Config.Ready)
                OpenSettings();
            Log("boot", null);
        }
        catch (Exception ex)
        {
            Log("startup", ex);
            MessageBox.Show(ex.ToString(), "PrintPilot Desk 启动失败");
            Shutdown();
        }
    }

    void ListenPing(CancellationToken ct)
    {
        try
        {
            while (!ct.IsCancellationRequested)
            {
                if (_ping is null || !_ping.WaitOne(500))
                    continue;
                Dispatcher.Invoke(() =>
                {
                    if (!Config.Ready)
                    {
                        OpenSettings();
                        return;
                    }
                    try
                    {
                        _tray?.ShowNotification("PrintPilot", "已经在托盘里。左键打开机台页。", NotificationIcon.Info);
                    }
                    catch (Exception ex) { Log("ping-notify", ex); }
                    ShowHover();
                });
            }
        }
        catch (ObjectDisposedException) { }
    }

    static void TrimLog()
    {
        try
        {
            var p = Path.Combine(AppContext.BaseDirectory, "printpilot-desk.log");
            if (!File.Exists(p))
                return;
            var lines = File.ReadAllLines(p);
            if (lines.Length > 200)
                File.WriteAllLines(p, lines[^200..]);
        }
        catch { /* ignore */ }
    }

    static void Log(string tag, Exception? ex)
    {
        try
        {
            var line = DateTime.Now.ToString("s") + " [" + tag + "] " + (ex?.ToString() ?? "ok") + Environment.NewLine;
            File.AppendAllText(Path.Combine(AppContext.BaseDirectory, "printpilot-desk.log"), line);
        }
        catch { /* ignore */ }
    }

    static Window CreateAnchor()
    {
        var w = new Window
        {
            Width = 1,
            Height = 1,
            WindowStyle = WindowStyle.None,
            AllowsTransparency = true,
            Background = Brushes.Transparent,
            ShowInTaskbar = false,
            ShowActivated = false,
            Topmost = true,
            ResizeMode = ResizeMode.NoResize,
            Opacity = 0,
            IsHitTestVisible = false,
            Left = -32000,
            Top = -32000,
        };
        w.Show();
        return w;
    }

    ContextMenu BuildMenu()
    {
        var menu = new ContextMenu
        {
            Style = TryFindResource("TrayMenu") as Style,
        };
        MenuItem Item(string header, RoutedEventHandler click)
        {
            var it = new MenuItem { Header = header, Style = TryFindResource("TrayMenuItem") as Style };
            it.Click += click;
            return it;
        }
        menu.Items.Add(Item("设置", (_, _) => OpenSettings()));
        menu.Items.Add(Item("打开机台页", (_, _) => OpenMachineSite()));
        menu.Items.Add(Item("打开网站", (_, _) => OpenSite("")));
        menu.Items.Add(new Separator { Style = TryFindResource("TraySeparator") as Style });
        menu.Items.Add(Item("退出", (_, _) => Shutdown()));
        menu.Closed += (_, _) => _menuOpen = false;
        return menu;
    }

    void ShowTrayMenu()
    {
        if (_tray?.ContextMenu is not { } menu || _anchor is null)
            return;
        SuppressHoverForMenu();
        if (menu.IsOpen)
            menu.IsOpen = false;
        GetCursorPos(out var pt);
        var scale = DpiScaleAt(pt);
        var dipX = pt.X / scale;
        var dipY = pt.Y / scale;
        var work = WorkAreaDip(pt, scale);

        menu.Measure(new Size(double.PositiveInfinity, double.PositiveInfinity));
        var mw = menu.DesiredSize.Width > 1 ? menu.DesiredSize.Width : 168;
        var mh = menu.DesiredSize.Height > 1 ? menu.DesiredSize.Height : 168;

        var x = dipX;
        var y = dipY - mh - 8;
        if (y < work.Top)
            y = dipY + 24;
        if (x + mw > work.Right)
            x = work.Right - mw - 8;
        if (x < work.Left)
            x = work.Left + 8;
        if (y + mh > work.Bottom)
            y = work.Bottom - mh - 8;

        _anchor.Left = x;
        _anchor.Top = y;
        if (!_anchor.IsVisible)
            _anchor.Show();

        menu.PlacementTarget = _anchor;
        menu.Placement = PlacementMode.AbsolutePoint;
        menu.HorizontalOffset = x;
        menu.VerticalOffset = y;
        menu.IsOpen = true;
        _menuOpen = true;
        try
        {
            SetForegroundWindow(new WindowInteropHelper(_anchor).EnsureHandle());
        }
        catch { /* 没有句柄时菜单仍能开 */ }
    }

    static double DpiScaleAt(NativePoint pt)
    {
        try
        {
            var mon = MonitorFromPoint(pt, 2);
            if (mon != IntPtr.Zero && GetDpiForMonitor(mon, 0, out var dx, out _) == 0 && dx > 0)
                return dx / 96.0;
        }
        catch { /* 退回 96dpi */ }
        return 1.0;
    }

    static Rect WorkAreaDip(NativePoint pt, double scale)
    {
        try
        {
            var mon = MonitorFromPoint(pt, 2);
            var info = new MonitorInfo { cbSize = Marshal.SizeOf<MonitorInfo>() };
            if (mon != IntPtr.Zero && GetMonitorInfo(mon, ref info))
            {
                var r = info.rcWork;
                return new Rect(r.Left / scale, r.Top / scale, (r.Right - r.Left) / scale, (r.Bottom - r.Top) / scale);
            }
        }
        catch { /* 用主屏 */ }
        return SystemParameters.WorkArea;
    }

    void OpenMachineSite() => OpenSite("/#/machine");

    void OpenSite(string hash)
    {
        _tray?.CloseTrayPopup();
        var url = string.IsNullOrWhiteSpace(Config.Url) ? "https://3d.bstccc.cn" : Config.Url.TrimEnd('/');
        Process.Start(new ProcessStartInfo(url + hash) { UseShellExecute = true });
    }

    void SuppressHoverForMenu()
    {
        _hoverDelay?.Stop();
        _leaveTimer?.Stop();
        _tray?.CloseTrayPopup();
    }

    void QueueHover()
    {
        if (_menuOpen || RightButtonDown() || _tray?.ContextMenu is { IsOpen: true })
        {
            _hoverDelay?.Stop();
            _tray?.CloseTrayPopup();
            return;
        }
        if (_tray?.TrayPopupResolved is { IsOpen: true })
        {
            _leaveTimer?.Start();
            return;
        }
        _hoverDelay?.Stop();
        _hoverDelay?.Start();
    }

    void ShowHover()
    {
        if (_tray is null || _menuOpen || RightButtonDown())
            return;
        if (_tray.TrayPopupResolved is { IsOpen: true })
            return;
        if (_tray.ContextMenu is { IsOpen: true })
            return;
        GetCursorPos(out _hoverAt);
        var dipW = 316.0;
        var dipH = 320.0;
        if (_hover is not null)
        {
            _hover.Measure(new Size(316, 900));
            if (_hover.DesiredSize.Width > 1)
                dipW = _hover.DesiredSize.Width;
            if (_hover.DesiredSize.Height > 1)
                dipH = _hover.DesiredSize.Height;
        }
        var scale = 1.0;
        try
        {
            if (_hover is not null)
                scale = VisualTreeHelper.GetDpi(_hover).PixelsPerDip;
        }
        catch { /* 还没进视觉树 */ }
        var cardW = (int)Math.Ceiling(dipW * scale);
        var cardH = (int)Math.Ceiling(dipH * scale);
        var x = Math.Max(8, _hoverAt.X - cardW / 2);
        var y = _hoverAt.Y - cardH - 20;
        if (y < 8)
            y = _hoverAt.Y + 36;
        _tray.ShowTrayPopup(new System.Drawing.Point(x, y));
        _leaveTimer?.Start();
    }

    void MaybeCloseHover()
    {
        if (_tray?.TrayPopupResolved is not { IsOpen: true })
        {
            _leaveTimer?.Stop();
            return;
        }
        GetCursorPos(out var pt);
        if (Near(_hoverAt, pt, 72))
            return;
        if (_tray.TrayPopupResolved.Child is FrameworkElement child && child.IsVisible && child.ActualWidth > 0)
        {
            try
            {
                var tl = child.PointToScreen(new Point(0, 0));
                var br = child.PointToScreen(new Point(child.RenderSize.Width, child.RenderSize.Height));
                if (pt.X >= tl.X - 10 && pt.X <= br.X + 10 && pt.Y >= tl.Y - 10 && pt.Y <= br.Y + 10)
                    return;
            }
            catch { /* popup tearing down */ }
        }
        _tray.CloseTrayPopup();
        _leaveTimer?.Stop();
    }

    static bool Near(NativePoint a, NativePoint b, int d) =>
        Math.Abs(a.X - b.X) <= d && Math.Abs(a.Y - b.Y) <= d;

    public void OpenSettings()
    {
        _tray?.CloseTrayPopup();
        if (_settings is { IsVisible: true })
        {
            _settings.Activate();
            return;
        }
        _settings = new SettingsWindow(Config, async () =>
        {
            TunePoll(Model.Printing);
            await RefreshAsync();
        });
        if (_anchor is not null)
            _settings.Owner = _anchor;
        _settings.Closed += (_, _) => _settings = null;
        _settings.Show();
        _settings.Activate();
    }

    async Task RefreshAsync()
    {
        if (Interlocked.Exchange(ref _busy, 1) == 1)
            return;
        try
        {
            var snap = await DeskSnapshot.FetchAsync(Config.Url, Config.Token);
            var printingNow = snap is { FetchError: "", Printing: true };
            if (_wasPrinting == true && !printingNow && snap.FetchError == "" && Config.NotifyDone)
            {
                var job = DeskSnapshot.Fmt(snap.Job);
                var msg = job == "—" ? "打印结束了。" : "打印结束了：" + job;
                try
                {
                    _tray?.ShowNotification("PrintPilot", msg, NotificationIcon.Info);
                }
                catch (Exception ex) { Log("notify", ex); }
            }
            if (_wasPrinting is not null || snap.FetchError == "")
                _wasPrinting = printingNow;

            if (snap.FetchError != "")
                _failStreak++;
            else
                _failStreak = 0;
            if (_failStreak >= 2)
                snap.FetchError = snap.FetchError + "（已连续失败）";

            Model.Apply(snap);
            if (_tray is not null)
            {
                var sig = $"{Model.Offline}|{Model.Printing}|{(int)Model.Progress}";
                if (sig != _iconSig)
                {
                    _iconSig = sig;
                    var next = TrayIconFactory.Create(Model);
                    var old = _tray.Icon;
                    _tray.Icon = next;
                    old?.Dispose();
                }
            }
            TunePoll(printingNow);
        }
        catch (Exception ex)
        {
            Log("refresh", ex);
        }
        finally
        {
            Interlocked.Exchange(ref _busy, 0);
        }
    }

    void TunePoll(bool printing)
    {
        if (_timer is null)
            return;
        var idle = Math.Clamp(Config.PollSeconds, 5, 300);
        var active = Math.Min(idle, 10);
        var sec = printing ? active : idle;
        var next = TimeSpan.FromSeconds(sec);
        if (Math.Abs((_timer.Interval - next).TotalMilliseconds) > 250)
            _timer.Interval = next;
    }

    void OnExit(object sender, ExitEventArgs e)
    {
        _timer?.Stop();
        _hoverDelay?.Stop();
        _leaveTimer?.Stop();
        _pingCts?.Cancel();
        try { _tray?.Icon?.Dispose(); } catch { /* ignore */ }
        _tray?.Dispose();
        try { _anchor?.Close(); } catch { /* ignore */ }
        _ping?.Dispose();
        try { _mutex?.ReleaseMutex(); } catch { /* abandoned */ }
        _mutex?.Dispose();
    }

    [StructLayout(LayoutKind.Sequential)]
    struct NativePoint
    {
        public int X;
        public int Y;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct RectWin
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct MonitorInfo
    {
        public int cbSize;
        public RectWin rcMonitor;
        public RectWin rcWork;
        public uint dwFlags;
    }

    [DllImport("user32.dll")]
    static extern bool GetCursorPos(out NativePoint lpPoint);

    [DllImport("user32.dll")]
    static extern short GetAsyncKeyState(int vKey);

    [DllImport("user32.dll")]
    static extern IntPtr MonitorFromPoint(NativePoint pt, uint dwFlags);

    [DllImport("user32.dll")]
    static extern bool GetMonitorInfo(IntPtr hMonitor, ref MonitorInfo lpmi);

    [DllImport("Shcore.dll")]
    static extern int GetDpiForMonitor(IntPtr hmonitor, int dpiType, out uint dpiX, out uint dpiY);

    [DllImport("user32.dll")]
    static extern bool SetForegroundWindow(IntPtr hWnd);

    static bool RightButtonDown() => (GetAsyncKeyState(0x02) & 0x8000) != 0;
}
