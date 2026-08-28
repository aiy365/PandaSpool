using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using SD = System.Drawing;

namespace PrintPilotDesk;

static class TrayIconFactory
{
    public static Icon Create(DeskViewModel vm)
    {
        using var bmp = new Bitmap(32, 32, PixelFormat.Format32bppArgb);
        using (var g = Graphics.FromImage(bmp))
        {
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.PixelOffsetMode = PixelOffsetMode.HighQuality;
            g.Clear(SD.Color.Transparent);

            SD.Color bg, fg, ring;
            string text;
            float sweep;
            if (vm.Offline)
            {
                bg = SD.Color.FromArgb(75, 85, 99);
                fg = SD.Color.White;
                ring = SD.Color.FromArgb(156, 163, 175);
                text = "!";
                sweep = 360;
            }
            else if (vm.Printing)
            {
                bg = SD.Color.FromArgb(17, 24, 39);
                fg = SD.Color.FromArgb(204, 251, 241);
                ring = SD.Color.FromArgb(45, 212, 191);
                var n = (int)Math.Round(vm.Progress);
                text = n >= 100 ? "OK" : n.ToString();
                sweep = (float)(Math.Clamp(vm.Progress / 100, 0.02, 1) * 360);
            }
            else
            {
                bg = SD.Color.FromArgb(22, 163, 74);
                fg = SD.Color.White;
                ring = SD.Color.FromArgb(187, 247, 208);
                text = "P";
                sweep = 360;
            }

            g.FillEllipse(new SolidBrush(bg), 1, 1, 30, 30);
            using var pen = new Pen(ring, 3.2f) { StartCap = LineCap.Round, EndCap = LineCap.Round };
            g.DrawArc(pen, 3.2f, 3.2f, 25.6f, 25.6f, -90, sweep);

            using var font = new Font("Segoe UI", text.Length > 2 ? 8 : (text.Length == 2 ? 10 : 12), SD.FontStyle.Bold, GraphicsUnit.Pixel);
            var sz = g.MeasureString(text, font);
            g.DrawString(text, font, new SolidBrush(fg), (32 - sz.Width) / 2, (32 - sz.Height) / 2);
        }

        var handle = bmp.GetHicon();
        try
        {
            using var tmp = Icon.FromHandle(handle);
            using var ms = new MemoryStream();
            tmp.Save(ms);
            ms.Position = 0;
            return new Icon(ms);
        }
        finally
        {
            DestroyIcon(handle);
        }
    }

    [DllImport("user32.dll", SetLastError = true)]
    static extern bool DestroyIcon(IntPtr hIcon);
}
