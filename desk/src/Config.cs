using System.Globalization;
using System.IO;
using System.Text;

namespace PrintPilotDesk;

public sealed class AppConfig
{
    public string Url { get; set; } = "https://3d.bstccc.cn";
    public string Token { get; set; } = "";
    public int PollSeconds { get; set; } = 30;
    public bool NotifyDone { get; set; } = true;
    public string Path { get; private set; } = "";

    public static AppConfig Load()
    {
        var cfg = new AppConfig { Path = FindIni() };
        if (!File.Exists(cfg.Path))
            return cfg;
        var section = "";
        foreach (var raw in File.ReadAllLines(cfg.Path))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith('#') || line.StartsWith(';'))
                continue;
            if (line.StartsWith('[') && line.EndsWith(']'))
            {
                section = line[1..^1].ToLowerInvariant();
                continue;
            }
            var i = line.IndexOf('=');
            if (i < 0)
                continue;
            var k = line[..i].Trim();
            var v = line[(i + 1)..].Trim();
            switch (section)
            {
                case "server":
                    if (k == "url")
                        cfg.Url = v.TrimEnd('/');
                    else if (k == "token")
                        cfg.Token = v;
                    break;
                case "poll":
                    if (k == "seconds" && int.TryParse(v, NumberStyles.Integer, CultureInfo.InvariantCulture, out var n) && n >= 5)
                        cfg.PollSeconds = Math.Clamp(n, 5, 300);
                    break;
                case "desk":
                    if (k == "notify_done")
                        cfg.NotifyDone = v is "1" or "true" or "yes";
                    break;
            }
        }
        return cfg;
    }

    public void Save()
    {
        PollSeconds = Math.Clamp(PollSeconds, 5, 300);
        Url = Url.Trim().TrimEnd('/');
        var sb = new StringBuilder();
        sb.AppendLine("[server]");
        sb.AppendLine($"url={Url}");
        sb.AppendLine($"token={Token}");
        sb.AppendLine();
        sb.AppendLine("[poll]");
        sb.AppendLine($"seconds={PollSeconds}");
        sb.AppendLine();
        sb.AppendLine("[desk]");
        sb.AppendLine($"notify_done={(NotifyDone ? "1" : "0")}");
        File.WriteAllText(Path, sb.ToString(), new UTF8Encoding(false));
    }

    public bool Ready => !string.IsNullOrWhiteSpace(Url) && !string.IsNullOrWhiteSpace(Token);

    static string FindIni()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 8 && dir is not null; i++)
        {
            var p = System.IO.Path.Combine(dir.FullName, "printpilot-desk.ini");
            if (File.Exists(p))
                return p;
            dir = dir.Parent;
        }
        return System.IO.Path.Combine(AppContext.BaseDirectory, "printpilot-desk.ini");
    }
}
