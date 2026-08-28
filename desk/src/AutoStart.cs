using Microsoft.Win32;
using System.IO;

namespace PrintPilotDesk;

static class AutoStart
{
    const string Key = @"Software\Microsoft\Windows\CurrentVersion\Run";
    const string Name = "PrintPilotDesk";

    public static bool IsEnabled()
    {
        using var k = Registry.CurrentUser.OpenSubKey(Key, false);
        return k?.GetValue(Name) is string s && s.Length > 0;
    }

    public static void Set(bool on)
    {
        using var k = Registry.CurrentUser.OpenSubKey(Key, true) ?? Registry.CurrentUser.CreateSubKey(Key);
        if (k is null)
            return;
        if (on)
        {
            var exe = Environment.ProcessPath ?? Path.Combine(AppContext.BaseDirectory, "printpilot-desk.exe");
            k.SetValue(Name, "\"" + exe + "\"");
        }
        else
        {
            k.DeleteValue(Name, false);
        }
    }
}
