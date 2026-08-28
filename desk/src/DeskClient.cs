using System.Globalization;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace PrintPilotDesk;

public sealed class DeskSnapshot
{
    public bool Ok { get; set; }
    public bool Connected { get; set; }
    public bool Printing { get; set; }
    public double Progress { get; set; }
    public double RemainingMin { get; set; }
    public string? Eta { get; set; }
    public string? GcodeState { get; set; }
    public string? Stage { get; set; }
    public JsonElement NozzleTemp { get; set; }
    public JsonElement NozzleTarget { get; set; }
    public JsonElement BedTemp { get; set; }
    public JsonElement BedTarget { get; set; }
    public JsonElement Layer { get; set; }
    public JsonElement TotalLayer { get; set; }
    public JsonElement Job { get; set; }
    public JsonElement PrintBoostActive { get; set; }
    public JsonElement Pm25 { get; set; }
    public JsonElement TempC { get; set; }
    public JsonElement Rh { get; set; }
    public JsonElement Presence { get; set; }
    public JsonElement AirTs { get; set; }
    public string FetchError { get; set; } = "";

    public bool Offline => FetchError != "" || !Ok;

    static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNameCaseInsensitive = true,
        NumberHandling = JsonNumberHandling.AllowReadingFromString,
    };

    public static async Task<DeskSnapshot> FetchAsync(string url, string token, CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(url) || string.IsNullOrWhiteSpace(token))
            return new DeskSnapshot { FetchError = "还没填网址或令牌" };

        try
        {
            using var req = new HttpRequestMessage(HttpMethod.Get, url.TrimEnd('/') + "/api/desk");
            req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            using var res = await Http.SendAsync(req, ct).ConfigureAwait(false);
            var raw = await res.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
            if (!res.IsSuccessStatusCode)
                return new DeskSnapshot { FetchError = $"HTTP {(int)res.StatusCode}" };
            var d = JsonSerializer.Deserialize<Wire>(raw, JsonOpts);
            if (d is null)
                return new DeskSnapshot { FetchError = "返回不是 JSON" };
            var snap = new DeskSnapshot
            {
                Ok = d.Ok,
                Connected = d.Connected,
                Printing = d.Printing,
                Progress = d.Progress,
                RemainingMin = d.RemainingMin,
                Eta = d.Eta,
                GcodeState = d.GcodeState,
                Stage = d.Stage,
                NozzleTemp = d.NozzleTemp,
                NozzleTarget = d.NozzleTarget,
                BedTemp = d.BedTemp,
                BedTarget = d.BedTarget,
                Layer = d.Layer,
                TotalLayer = d.TotalLayer,
                Job = d.Job,
                PrintBoostActive = d.PrintBoostActive,
                Pm25 = d.Pm25,
                TempC = d.TempC,
                Rh = d.Rh,
                Presence = d.Presence,
                AirTs = d.AirTs,
            };
            if (snap.Printing && string.IsNullOrWhiteSpace(snap.Eta) && snap.RemainingMin > 0)
                snap.Eta = DateTime.Now.AddMinutes(snap.RemainingMin).ToString("HH:mm");
            return snap;
        }
        catch (TaskCanceledException)
        {
            return new DeskSnapshot { FetchError = "请求超时" };
        }
        catch (Exception ex)
        {
            return new DeskSnapshot { FetchError = Short(ex.Message) };
        }
    }

    public static string Fmt(JsonElement el)
    {
        switch (el.ValueKind)
        {
            case JsonValueKind.Null:
            case JsonValueKind.Undefined:
                return "—";
            case JsonValueKind.String:
                var s = el.GetString();
                return string.IsNullOrWhiteSpace(s) ? "—" : s!;
            case JsonValueKind.True:
                return "是";
            case JsonValueKind.False:
                return "否";
            case JsonValueKind.Number:
                if (el.TryGetInt64(out var n))
                    return n.ToString(CultureInfo.InvariantCulture);
                if (el.TryGetDouble(out var f))
                    return f.ToString(Math.Abs(f - Math.Round(f)) < 0.05 ? "0" : "0.0", CultureInfo.InvariantCulture);
                return el.ToString();
            default:
                var t = el.ToString();
                return string.IsNullOrWhiteSpace(t) ? "—" : t;
        }
    }

    static string Short(string s) => s.Length <= 80 ? s : s[..80];

    static readonly HttpClient Http = new()
    {
        Timeout = TimeSpan.FromSeconds(8),
    };

    sealed class Wire
    {
        [JsonPropertyName("ok")] public bool Ok { get; set; }
        [JsonPropertyName("connected")] public bool Connected { get; set; }
        [JsonPropertyName("printing")] public bool Printing { get; set; }
        [JsonPropertyName("progress")] public double Progress { get; set; }
        [JsonPropertyName("remaining_min")] public double RemainingMin { get; set; }
        [JsonPropertyName("eta")] public string? Eta { get; set; }
        [JsonPropertyName("gcode_state")] public string? GcodeState { get; set; }
        [JsonPropertyName("stage")] public string? Stage { get; set; }
        [JsonPropertyName("nozzle_temp")] public JsonElement NozzleTemp { get; set; }
        [JsonPropertyName("nozzle_target")] public JsonElement NozzleTarget { get; set; }
        [JsonPropertyName("bed_temp")] public JsonElement BedTemp { get; set; }
        [JsonPropertyName("bed_target")] public JsonElement BedTarget { get; set; }
        [JsonPropertyName("layer")] public JsonElement Layer { get; set; }
        [JsonPropertyName("total_layer")] public JsonElement TotalLayer { get; set; }
        [JsonPropertyName("job")] public JsonElement Job { get; set; }
        [JsonPropertyName("print_boost_active")] public JsonElement PrintBoostActive { get; set; }
        [JsonPropertyName("pm25")] public JsonElement Pm25 { get; set; }
        [JsonPropertyName("t_c")] public JsonElement TempC { get; set; }
        [JsonPropertyName("rh")] public JsonElement Rh { get; set; }
        [JsonPropertyName("presence")] public JsonElement Presence { get; set; }
        [JsonPropertyName("air_ts")] public JsonElement AirTs { get; set; }
    }
}
