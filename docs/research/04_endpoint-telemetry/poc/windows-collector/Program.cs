using System.Diagnostics;
using System.Management;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using System.Windows.Forms;

// Research collector: current interactive session only; no clipboard payload,
// keyboard hooks, network transmission, installation, or autostart.
internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        int seconds = 120;
        string directory = "logs";
        bool titles = false;
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--window-titles") titles = true;
            else if (args[i] == "--seconds" && i + 1 < args.Length &&
                     int.TryParse(args[++i], out int n) && n > 0 && n <= 86400) seconds = n;
            else if (args[i] == "--out" && i + 1 < args.Length) directory = args[++i];
            else
            {
                Console.Error.WriteLine("Usage: RealtimeCollector [--seconds 120] [--out logs] [--window-titles]");
                return 1;
            }
        }
        try
        {
            using var log = new EventLogWriter(directory);
            using var collector = new Collector(log, titles);
            Console.WriteLine($"Research collection for {seconds}s. Ctrl+C stops. File: {log.Path}");
            Console.WriteLine($"Clipboard payload: OFF. Window title capture: {titles}.");
            collector.Start();
            ConsoleCancelEventHandler cancel = (_, e) =>
            {
                e.Cancel = true;
                Native.PostMessage(collector.Handle, 0x0010, 0, 0);
            };
            Console.CancelKeyPress += cancel;
            using var timer = new System.Windows.Forms.Timer { Interval = 1000 };
            var elapsed = Stopwatch.StartNew();
            int ticks = 0;
            timer.Tick += (_, _) =>
            {
                if (++ticks % 10 == 0)
                    log.Emit("heartbeat", new { queue_drops = log.Dropped, elapsed_ms = elapsed.ElapsedMilliseconds });
                if (elapsed.Elapsed.TotalSeconds >= seconds) Application.ExitThread();
            };
            timer.Start();
            try { Application.Run(); }
            finally
            {
                timer.Stop();
                Console.CancelKeyPress -= cancel;
                collector.Stop();
            }
            Console.WriteLine($"Stopped. Queue drops: {log.Dropped}. Check source_status and error events.");
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Collector failed: {ex.GetType().Name}: {ex.Message}");
            return 2;
        }
    }
}

internal sealed class EventLogWriter : IDisposable
{
    private readonly Channel<object> queue = Channel.CreateBounded<object>(new BoundedChannelOptions(4096)
    { SingleReader = true, FullMode = BoundedChannelFullMode.Wait });
    private readonly Task writer;
    private readonly Stopwatch clock = Stopwatch.StartNew();
    private readonly object gate = new();
    private long counter, dropped;
    private bool closed;
    public readonly string RunId = Guid.NewGuid().ToString();
    public string Path { get; }
    public long Dropped => Interlocked.Read(ref dropped);

    public EventLogWriter(string directory)
    {
        Directory.CreateDirectory(directory);
        Path = System.IO.Path.GetFullPath(System.IO.Path.Combine(directory,
            $"events-{DateTime.UtcNow:yyyyMMddTHHmmssZ}-{RunId}.jsonl"));
        // Open synchronously so path/permission errors fail before starting sensors.
        var output = new StreamWriter(new FileStream(Path, FileMode.CreateNew, FileAccess.Write,
            FileShare.Read), new UTF8Encoding(false)) { AutoFlush = true };
        writer = Task.Run(async () =>
        {
            try
            {
                using (output)
                    await foreach (var row in queue.Reader.ReadAllAsync())
                        await output.WriteLineAsync(JsonSerializer.Serialize(row));
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Log write failed; stopping: {ex.Message}");
                Environment.Exit(2);
            }
        });
    }

    private object Row(string type, object data) => new
    {
        schema_version = 2, run_id = RunId, event_id = ++counter,
        observed_at_utc = DateTimeOffset.UtcNow.ToString("O"),
        monotonic_ms = clock.Elapsed.TotalMilliseconds, type, data
    };

    public void Emit(string type, object data)
    {
        lock (gate)
        {
            if (closed) return;
            if (!queue.Writer.TryWrite(Row(type, data))) Interlocked.Increment(ref dropped);
        }
    }

    public void Dispose()
    {
        object last;
        lock (gate)
        {
            if (closed) return;
            closed = true;
            last = Row("collector_stop", new { queue_drops = Dropped,
                note = "Queue drops only; upstream OS/WMI losses are not measured." });
        }
        queue.Writer.WriteAsync(last).AsTask().GetAwaiter().GetResult();
        queue.Writer.TryComplete();
        writer.GetAwaiter().GetResult();
    }
}

internal sealed class Collector : NativeWindow, IDisposable
{
    private readonly EventLogWriter log;
    private readonly bool titles;
    private readonly int session = Process.GetCurrentProcess().SessionId;
    private readonly Native.WinEventProc callback;
    private readonly List<nint> hooks = new();
    private readonly List<ManagementEventWatcher> watchers = new();
    private readonly object processGate = new();
    private readonly Dictionary<uint, string> sessionProcesses = new();
    private bool clipboardRegistered;
    private volatile bool stopped;

    public Collector(EventLogWriter log, bool titles)
    {
        this.log = log;
        this.titles = titles;
        callback = OnWinEvent; // Keep delegate rooted until all hooks are removed.
        CreateHandle(new CreateParams { Caption = "Capstone Research Collector", Parent = new nint(-3) });
    }

    public void Start()
    {
        using var identity = WindowsIdentity.GetCurrent();
        log.Emit("collector_start", new
        {
            machine = Environment.MachineName, user_sid = identity.User?.Value,
            session_id = session, process_id = Environment.ProcessId,
            os = Environment.OSVersion.VersionString, runtime = Environment.Version.ToString(),
            architecture = RuntimeInformation.ProcessArchitecture.ToString(),
            elevated = new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator),
            window_titles = titles, clipboard_payload = false,
            foreground_scope = "current desktop", process_scope = "current session"
        });
        clipboardRegistered = Native.AddClipboardFormatListener(Handle);
        log.Emit("source_status", new { source = "clipboard", enabled = clipboardRegistered,
            win32_error = clipboardRegistered ? 0 : Marshal.GetLastWin32Error() });
        AddHook(3, "foreground"); // EVENT_SYSTEM_FOREGROUND
        if (titles) AddHook(0x800C, "foreground_title_change");
        StartWatcher("Win32_ProcessStartTrace", "process_start");
        StartWatcher("Win32_ProcessStopTrace", "process_stop");
        // Snapshot is observed at collector start, not a historical start event.
        foreach (var p in Process.GetProcesses())
        {
            using (p)
            {
                try
                {
                    if (p.SessionId != session) continue;
                    lock (processGate) sessionProcesses.TryAdd((uint)p.Id, p.ProcessName);
                    log.Emit("process_snapshot", new { pid = p.Id, process_name = p.ProcessName,
                        session_id = session, process_start_utc = p.StartTime.ToUniversalTime().ToString("O") });
                }
                catch (Exception ex)
                {
                    log.Emit("snapshot_unavailable", new { pid = p.Id, reason = ex.GetType().Name });
                }
            }
        }
        WindowEvent("foreground_snapshot", Native.GetForegroundWindow(), null);
    }

    private void AddHook(uint code, string source)
    {
        nint h = Native.SetWinEventHook(code, code, 0, callback, 0, 0, 2); // OUTOFCONTEXT | SKIPOWNPROCESS
        if (h != 0) hooks.Add(h);
        log.Emit("source_status", new { source, enabled = h != 0 });
    }

    private void StartWatcher(string className, string type)
    {
        ManagementEventWatcher? watcher = null;
        try
        {
            // StopTrace can report SessionID=0 even for an observed interactive process.
            // Subscribe without that provider-side filter, then correlate known PIDs/names.
            string query = type == "process_stop" ? $"SELECT * FROM {className}" :
                $"SELECT * FROM {className} WHERE SessionID = {session}";
            watcher = new ManagementEventWatcher(new WqlEventQuery(query));
            watcher.EventArrived += (_, e) =>
            {
                if (stopped) return;
                try
                {
                    using var item = e.NewEvent;
                    uint pid = Convert.ToUInt32(item["ProcessID"]);
                    uint sourceSession = Convert.ToUInt32(item["SessionID"]);
                    string name = Convert.ToString(item["ProcessName"]) ?? "";
                    string attribution = "source_session";
                    lock (processGate)
                    {
                        if (type == "process_start") sessionProcesses[pid] = name;
                        else
                        {
                            bool known = sessionProcesses.TryGetValue(pid, out string? knownName) &&
                                string.Equals(System.IO.Path.GetFileNameWithoutExtension(knownName),
                                    System.IO.Path.GetFileNameWithoutExtension(name), StringComparison.OrdinalIgnoreCase);
                            if (sourceSession != session && !known) return;
                            sessionProcesses.Remove(pid);
                            if (sourceSession != session) attribution = "cached_pid_name_candidate";
                        }
                    }
                    ulong raw = Convert.ToUInt64(item["TIME_CREATED"]);
                    log.Emit(type, new
                    {
                        pid,
                        parent_pid = Convert.ToUInt32(item["ParentProcessID"]),
                        process_name = name,
                        session_id = sourceSession,
                        collector_session_id = session,
                        session_attribution = attribution,
                        instance_identity_verified = false,
                        source_time_filetime = raw.ToString(),
                        source_time_utc = DateTime.FromFileTimeUtc(checked((long)raw)).ToString("O"),
                        source_time_semantics = "WMI event generation time",
                        exit_status = type == "process_stop" ? Convert.ToUInt32(item["ExitStatus"]) : (uint?)null
                    });
                }
                catch (Exception ex) { log.Emit("collector_error", new { source = type, reason = ex.Message }); }
            };
            watcher.Stopped += (_, e) =>
            {
                if (!stopped) log.Emit("source_status", new
                    { source = type, enabled = false, status = e.Status.ToString() });
            };
            watcher.Start();
            watchers.Add(watcher);
            log.Emit("source_status", new { source = type, enabled = true });
        }
        catch (Exception ex)
        {
            watcher?.Dispose();
            Console.Error.WriteLine($"{type} unavailable: {ex.Message}");
            log.Emit("source_status", new { source = type, enabled = false, reason = ex.Message });
        }
    }

    private void OnWinEvent(nint hook, uint code, nint hwnd, int obj, int child, uint thread, uint tick)
    {
        if (stopped) return;
        try
        {
            if (code == 0x800C && (obj != 0 || child != 0 || hwnd != Native.GetForegroundWindow())) return;
            WindowEvent(code == 3 ? "foreground_change" : "foreground_title_change", hwnd, tick);
        }
        catch (Exception ex) { log.Emit("collector_error", new { source = "winevent", reason = ex.Message }); }
    }

    private object WindowInfo(nint hwnd)
    {
        Native.GetWindowThreadProcessId(hwnd, out uint pid);
        string? title = null;
        if (titles && pid != Environment.ProcessId)
        {
            var buffer = new StringBuilder(1024);
            Native.GetWindowTextW(hwnd, buffer, buffer.Capacity);
            title = buffer.ToString();
        }
        return new { hwnd = hwnd.ToInt64().ToString("X"), pid, title,
            title_limit_chars = titles ? 1023 : 0,
            note = "Metadata queried at observation; handles/PIDs can be reused. Title is not URL." };
    }

    private void WindowEvent(string type, nint hwnd, uint? tick) => log.Emit(type, new
    {
        window = WindowInfo(hwnd), source_event_tick_ms = tick,
        source_time_semantics = "WinEvent uptime tick if present; not a UTC timestamp"
    });

    protected override void WndProc(ref Message m)
    {
        if (m.Msg == 0x031D && !stopped) // WM_CLIPBOARDUPDATE
        {
            try { ClipboardEvent(); }
            catch (Exception ex) { log.Emit("collector_error", new { source = "clipboard", reason = ex.Message }); }
        }
        if (m.Msg == 0x0010) { Application.ExitThread(); return; }
        base.WndProc(ref m);
    }

    private void ClipboardEvent()
    {
        uint before = Native.GetClipboardSequenceNumber();
        var owner = WindowInfo(Native.GetClipboardOwner());
        var foreground = WindowInfo(Native.GetForegroundWindow());
        var formats = new List<uint>();
        // Bounded synchronous retry: at most 100 ms of intentional GUI-thread delay.
        // Never attach a later clipboard state to this observation.
        var retryClock = Stopwatch.StartNew();
        bool opened = false;
        bool superseded = false;
        int attempts = 0;
        int error = 0;
        var openErrors = new List<int>();
        for (int attempt = 0; attempt < 5; attempt++)
        {
            if (attempt > 0) System.Threading.Thread.Sleep(25);
            uint current = Native.GetClipboardSequenceNumber();
            if (before == 0 || current == 0 || current != before)
            {
                superseded = current != before;
                break;
            }
            attempts++;
            opened = Native.OpenClipboard(Handle);
            error = opened ? 0 : Marshal.GetLastWin32Error();
            if (opened) break;
            openErrors.Add(error);
        }
        int enumError = 0;
        bool formatLimit = false;
        if (opened)
        {
            try
            {
                // Recheck after acquiring access; the state could change between calls.
                uint lockedSequence = Native.GetClipboardSequenceNumber();
                superseded = lockedSequence != before;
                uint f = 0;
                while (!superseded && lockedSequence != 0 && formats.Count < 256)
                {
                    Marshal.SetLastPInvokeError(0);
                    f = Native.EnumClipboardFormats(f);
                    if (f == 0) { enumError = Marshal.GetLastWin32Error(); break; }
                    formats.Add(f);
                }
                formatLimit = formats.Count == 256;
            }
            finally { Native.CloseClipboard(); }
        }
        uint after = Native.GetClipboardSequenceNumber();
        bool sequenceValid = before != 0 && after != 0;
        bool changed = superseded || before != after;
        string formatStatus = !sequenceValid ? "sequence_unavailable" : changed ? "superseded" :
            !opened ? "open_failed" : enumError != 0 ? "enumeration_failed" :
            formatLimit ? "truncated" : "success";
        bool formatsKnown = formatStatus == "success";
        log.Emit("clipboard_update", new
        {
            sequence_before = before, sequence_after = after, changed_during_observation = changed,
            owner_at_observation = owner, foreground_at_observation = foreground,
            clipboard_opened = opened, win32_error = error, enum_error = enumError,
            open_attempts = attempts, open_errors = openErrors,
            retry_interval_ms = 25, max_open_attempts = 5,
            format_query_elapsed_ms = retryClock.Elapsed.TotalMilliseconds,
            format_query_status = formatStatus,
            format_ids = formatsKnown ? formats : null, format_limit_reached = formatLimit,
            has_unicode_text = formatsKnown ? (bool?)formats.Contains(13) : null,
            has_file_drop = formatsKnown ? (bool?)formats.Contains(15) : null,
            has_bitmap_or_dib = formatsKnown ? (bool?)(formats.Contains(2) || formats.Contains(8) || formats.Contains(17)) : null,
            payload_collected = false,
            semantics = "Clipboard state observed after notification; not a paste event or guaranteed copy source."
        });
    }

    public void Stop()
    {
        if (stopped) return;
        stopped = true;
        foreach (var watcher in watchers)
        {
            try { watcher.Stop(); }
            catch (Exception ex) { log.Emit("collector_error", new { source = "shutdown", reason = ex.Message }); }
            watcher.Dispose();
        }
        foreach (nint h in hooks) Native.UnhookWinEvent(h);
        if (clipboardRegistered) Native.RemoveClipboardFormatListener(Handle);
    }
    public void Dispose() { Stop(); DestroyHandle(); GC.KeepAlive(callback); }
}

internal static class Native
{
    internal delegate void WinEventProc(nint hook, uint code, nint hwnd, int obj, int child, uint thread, uint tick);
    [DllImport("user32.dll", SetLastError = true)] internal static extern bool AddClipboardFormatListener(nint hwnd);
    [DllImport("user32.dll")] internal static extern bool RemoveClipboardFormatListener(nint hwnd);
    [DllImport("user32.dll")] internal static extern nint SetWinEventHook(uint min, uint max, nint module,
        WinEventProc callback, uint process, uint thread, uint flags);
    [DllImport("user32.dll")] internal static extern bool UnhookWinEvent(nint hook);
    [DllImport("user32.dll")] internal static extern nint GetForegroundWindow();
    [DllImport("user32.dll")] internal static extern uint GetWindowThreadProcessId(nint hwnd, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] internal static extern int GetWindowTextW(nint hwnd, StringBuilder text, int max);
    [DllImport("user32.dll")] internal static extern uint GetClipboardSequenceNumber();
    [DllImport("user32.dll")] internal static extern nint GetClipboardOwner();
    [DllImport("user32.dll", SetLastError = true)] internal static extern bool OpenClipboard(nint hwnd);
    [DllImport("user32.dll", SetLastError = true)] internal static extern uint EnumClipboardFormats(uint format);
    [DllImport("user32.dll")] internal static extern bool CloseClipboard();
    [DllImport("user32.dll")] internal static extern bool PostMessage(nint hwnd, uint msg, nint wparam, nint lparam);
}
