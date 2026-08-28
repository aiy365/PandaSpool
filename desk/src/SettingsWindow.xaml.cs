using System.Windows;

namespace PrintPilotDesk;

public partial class SettingsWindow : Window
{
    readonly AppConfig _cfg;
    readonly Func<Task> _afterSave;

    public SettingsWindow(AppConfig cfg, Func<Task> afterSave)
    {
        InitializeComponent();
        _cfg = cfg;
        _afterSave = afterSave;
        UrlBox.Text = cfg.Url;
        TokenBox.Password = cfg.Token;
        PollSlider.Value = cfg.PollSeconds;
        PollLabel.Text = cfg.PollSeconds.ToString();
        AutoStartBox.IsChecked = AutoStart.IsEnabled();
        NotifyBox.IsChecked = cfg.NotifyDone;
    }

    void OnPollChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (PollLabel is not null)
            PollLabel.Text = ((int)PollSlider.Value).ToString();
    }

    async void OnTest(object sender, RoutedEventArgs e)
    {
        if (sender is System.Windows.Controls.Button b)
            b.IsEnabled = false;
        StatusText.Foreground = (System.Windows.Media.Brush)FindResource("Muted");
        StatusText.Text = "正在测…";
        try
        {
            var d = await DeskSnapshot.FetchAsync(UrlBox.Text.Trim(), TokenBox.Password);
            if (d.FetchError != "")
            {
                StatusText.Foreground = (System.Windows.Media.Brush)FindResource("Bad");
                StatusText.Text = d.FetchError;
                return;
            }
            StatusText.Foreground = (System.Windows.Media.Brush)FindResource("Good");
            StatusText.Text = d.Connected
                ? (d.Printing ? $"通了。正在打印 {d.Progress:0}%。" : "通了。打印机空闲。")
                : "Hub 通了，拓竹 MQTT 还没连上。";
        }
        finally
        {
            if (sender is System.Windows.Controls.Button b2)
                b2.IsEnabled = true;
        }
    }

    async void OnSave(object sender, RoutedEventArgs e)
    {
        if (sender is System.Windows.Controls.Button b)
            b.IsEnabled = false;
        _cfg.Url = UrlBox.Text.Trim();
        _cfg.Token = TokenBox.Password.Trim();
        _cfg.PollSeconds = (int)PollSlider.Value;
        _cfg.NotifyDone = NotifyBox.IsChecked == true;
        try
        {
            AutoStart.Set(AutoStartBox.IsChecked == true);
            _cfg.Save();
        }
        catch (Exception ex)
        {
            StatusText.Foreground = (System.Windows.Media.Brush)FindResource("Bad");
            StatusText.Text = (ex.Message.Contains("Run") || ex.Message.Contains("注册") ? "开机启动写不进：" : "写不进配置：") + ex.Message;
            if (sender is System.Windows.Controls.Button b2)
                b2.IsEnabled = true;
            return;
        }
        try
        {
            await _afterSave();
            Close();
        }
        catch (Exception ex)
        {
            StatusText.Foreground = (System.Windows.Media.Brush)FindResource("Bad");
            StatusText.Text = "保存后刷新失败：" + ex.Message;
            if (sender is System.Windows.Controls.Button b3)
                b3.IsEnabled = true;
        }
    }
}
