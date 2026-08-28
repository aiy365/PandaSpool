package main

import (
	"fmt"
	"strings"
	"sync"
	"syscall"
	"time"
	"unsafe"

	"golang.org/x/sys/windows"
)

type App struct {
	cfg     *Config
	mu      sync.Mutex
	desk    Desk
	hwnd    windows.Handle
	hover   windows.Handle
	settings windows.Handle
	nid     NOTIFYICONDATA
	icon    windows.Handle
	brush   windows.Handle
	hideAt   time.Time
	lastPoll time.Time
	inst     windows.Handle
}

var app *App

func (a *App) run() error {
	inst, _, _ := procGetModuleHandleW.Call(0)
	a.inst = windows.Handle(inst)
	br, _, _ := procCreateSolidBrush.Call(rgb(28, 32, 38))
	a.brush = windows.Handle(br)

	if err := a.regClass("PPDeskHidden", syscall.NewCallback(hiddenProc)); err != nil {
		return err
	}
	if err := a.regClass("PPDeskHover", syscall.NewCallback(hoverProc)); err != nil {
		return err
	}
	if err := a.regClass("PPDeskSettings", syscall.NewCallback(settingsProc)); err != nil {
		return err
	}

	hwnd, _, _ := procCreateWindowExW.Call(0, uintptr(unsafe.Pointer(utf16Ptr("PPDeskHidden"))), 0, 0, 0, 0, 0, 0, 0, 0, uintptr(a.inst), 0)
	if hwnd == 0 {
		return fmt.Errorf("create hidden window")
	}
	a.hwnd = windows.Handle(hwnd)

	hh, _, _ := procCreateWindowExW.Call(
		WS_EX_TOPMOST|WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE,
		uintptr(unsafe.Pointer(utf16Ptr("PPDeskHover"))),
		uintptr(unsafe.Pointer(utf16Ptr("PandaSpool"))),
		uintptr(WS_POPUP|0x00800000), // WS_BORDER
		0, 0, 280, 220,
		0, 0, uintptr(a.inst), 0,
	)
	a.hover = windows.Handle(hh)

	a.addTray()
	procSetTimer.Call(uintptr(a.hwnd), 1, 5000, 0)
	a.refresh()
	a.lastPoll = time.Now()

	url, token, _, _ := a.cfg.snapshot()
	if url == "" || token == "" {
		a.openSettings()
	}

	var msg MSG
	for {
		r, _, _ := procGetMessageW.Call(uintptr(unsafe.Pointer(&msg)), 0, 0, 0)
		if int32(r) <= 0 {
			break
		}
		procTranslateMessage.Call(uintptr(unsafe.Pointer(&msg)))
		procDispatchMessageW.Call(uintptr(unsafe.Pointer(&msg)))
	}
	return nil
}

func (a *App) regClass(name string, procCB uintptr) error {
	var wc WNDCLASSEX
	wc.CbSize = uint32(unsafe.Sizeof(wc))
	wc.LpfnWndProc = procCB
	wc.HInstance = a.inst
	cur, _, _ := procLoadCursorW.Call(0, uintptr(IDC_ARROW))
	wc.HCursor = windows.Handle(cur)
	wc.HbrBackground = windows.Handle(a.brush)
	wc.LpszClassName = utf16Ptr(name)
	r, _, err := procRegisterClassExW.Call(uintptr(unsafe.Pointer(&wc)))
	if r == 0 {
		return err
	}
	return nil
}

func (a *App) addTray() {
	a.nid.CbSize = uint32(unsafe.Sizeof(a.nid))
	a.nid.HWnd = a.hwnd
	a.nid.UID = 1
	a.nid.UFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP | NIF_SHOWTIP
	a.nid.UCallbackMessage = WM_TRAY
	copyUTF16(a.nid.SzTip[:], "PandaSpool")
	a.nid.HIcon = hiconFromRGBA(drawIcon(32, false, 0, false))
	a.icon = a.nid.HIcon
	procShell_NotifyIconW.Call(NIM_ADD, uintptr(unsafe.Pointer(&a.nid)))
	a.nid.UVersion = NOTIFYICON_VERSION_4
	procShell_NotifyIconW.Call(NIM_SETVERSION, uintptr(unsafe.Pointer(&a.nid)))
}

func (a *App) updateTray(tip string) {
	copyUTF16(a.nid.SzTip[:], tip)
	offline := a.desk.FetchErr != ""
	img := drawIcon(32, a.desk.Printing && !offline, a.desk.Progress, offline)
	newIcon := hiconFromRGBA(img)
	if newIcon != 0 {
		old := a.nid.HIcon
		a.nid.HIcon = newIcon
		a.icon = newIcon
		if old != 0 {
			procDestroyIcon.Call(uintptr(old))
		}
	}
	a.nid.UFlags = NIF_ICON | NIF_TIP | NIF_SHOWTIP
	procShell_NotifyIconW.Call(NIM_MODIFY, uintptr(unsafe.Pointer(&a.nid)))
}

func (a *App) removeTray() {
	procShell_NotifyIconW.Call(NIM_DELETE, uintptr(unsafe.Pointer(&a.nid)))
	if a.nid.HIcon != 0 {
		procDestroyIcon.Call(uintptr(a.nid.HIcon))
	}
}

func (a *App) refresh() {
	url, token, _, _ := a.cfg.snapshot()
	d := fetchDesk(url, token)
	a.mu.Lock()
	a.desk = d
	a.mu.Unlock()
	tip := "PandaSpool"
	if d.FetchErr != "" {
		tip = "PandaSpool · " + d.FetchErr
	} else if d.Printing {
		tip = "打印中"
		if d.ETA != "" {
			tip += " 完成 " + d.ETA
		}
	} else {
		tip = "空闲"
	}
	a.updateTray(tip)
	if visible(a.hover) {
		procInvalidateRect.Call(uintptr(a.hover), 0, 1)
	}
}

func hiddenProc(hwnd windows.Handle, msg uint32, w, l uintptr) uintptr {
	switch msg {
	case WM_TRAY:
		ev := loWord(l)
		switch ev {
		case uint16(WM_LBUTTONUP), uint16(NIN_SELECT), uint16(NIN_KEYSELECT):
			app.openSettings()
		case uint16(NIN_POPUPOPEN):
			app.showHover()
		case uint16(NIN_POPUPCLOSE):
			app.hideHoverSoon()
		case uint16(WM_RBUTTONUP), uint16(WM_RBUTTONDOWN), uint16(WM_CONTEXTMENU):
			app.trayMenu()
		}
		return 0
	case WM_CONTEXTMENU:
		app.trayMenu()
		return 0
	case WM_TIMER:
		if w == 1 {
			app.tickPoll()
		}
		if w == 2 {
			app.maybeHideHover()
		}
		return 0
	case WM_DESTROY:
		app.removeTray()
		procPostQuitMessage.Call(0)
		return 0
	}
	r, _, _ := procDefWindowProcW.Call(uintptr(hwnd), uintptr(msg), w, l)
	return r
}

func (a *App) tickPoll() {
	_, _, poll, _ := a.cfg.snapshot()
	if poll < 2 {
		poll = 5
	}
	if time.Since(a.lastPoll) >= time.Duration(poll)*time.Second {
		a.lastPoll = time.Now()
		a.refresh()
	}
}

func (a *App) trayMenu() {
	procSetForegroundWindow.Call(uintptr(a.hwnd))
	menu, _, _ := procCreatePopupMenu.Call()
	if menu == 0 {
		return
	}
	procAppendMenuW.Call(menu, MF_STRING, IDM_SETTINGS, uintptr(unsafe.Pointer(utf16Ptr("设置"))))
	procAppendMenuW.Call(menu, MF_SEPARATOR, 0, 0)
	procAppendMenuW.Call(menu, MF_STRING, IDM_EXIT, uintptr(unsafe.Pointer(utf16Ptr("退出"))))
	var pt POINT
	procGetCursorPos.Call(uintptr(unsafe.Pointer(&pt)))
	cmd, _, _ := procTrackPopupMenu.Call(menu, TPM_RIGHTBUTTON|TPM_RETURNCMD|TPM_BOTTOMALIGN, uintptr(pt.X), uintptr(pt.Y), 0, uintptr(a.hwnd), 0)
	procDestroyMenu.Call(menu)
	procPostMessageW.Call(uintptr(a.hwnd), WM_NULL, 0, 0)
	switch cmd {
	case IDM_SETTINGS:
		a.openSettings()
	case IDM_EXIT:
		procDestroyWindow.Call(uintptr(a.hwnd))
	}
}

func (a *App) showHover() {
	a.placeHover()
	procShowWindow.Call(uintptr(a.hover), SW_SHOWNA)
	procInvalidateRect.Call(uintptr(a.hover), 0, 1)
	a.hideAt = time.Time{}
}

func (a *App) hideHoverSoon() {
	a.hideAt = time.Now().Add(250 * time.Millisecond)
	procSetTimer.Call(uintptr(a.hwnd), 2, 280, 0)
}

func (a *App) maybeHideHover() {
	if a.hideAt.IsZero() || time.Now().Before(a.hideAt) {
		return
	}
	var pt POINT
	procGetCursorPos.Call(uintptr(unsafe.Pointer(&pt)))
	var rc RECT
	procGetWindowRect.Call(uintptr(a.hover), uintptr(unsafe.Pointer(&rc)))
	if pt.X >= rc.Left && pt.X <= rc.Right && pt.Y >= rc.Top && pt.Y <= rc.Bottom {
		a.hideAt = time.Time{}
		return
	}
	procShowWindow.Call(uintptr(a.hover), SW_HIDE)
	procKillTimer.Call(uintptr(a.hwnd), 2)
}

func (a *App) placeHover() {
	var ident NOTIFYICONIDENTIFIER
	ident.CbSize = uint32(unsafe.Sizeof(ident))
	ident.HWnd = a.hwnd
	ident.UID = 1
	var rc RECT
	r, _, _ := procShell_NotifyIconGetRect.Call(uintptr(unsafe.Pointer(&ident)), uintptr(unsafe.Pointer(&rc)))
	w, h := int32(340), int32(a.hoverHeight())
	var x, y int32
	if r == 0 { // S_OK
		x = (rc.Left+rc.Right)/2 - w/2
		y = rc.Top - h - 8
		if y < 8 {
			y = rc.Bottom + 8
		}
	} else {
		var pt POINT
		procGetCursorPos.Call(uintptr(unsafe.Pointer(&pt)))
		x, y = pt.X-w/2, pt.Y-h-16
	}
	if x < 8 {
		x = 8
	}
	procMoveWindow.Call(uintptr(a.hover), uintptr(x), uintptr(y), uintptr(w), uintptr(h), 1)
}

func (a *App) hoverHeight() int {
	lines := a.hoverLines()
	return 18 + len(lines)*20 + 12
}

func (a *App) hoverLines() []string {
	a.mu.Lock()
	d := a.desk
	a.mu.Unlock()
	if d.FetchErr != "" {
		return []string{"PandaSpool", d.FetchErr, "右击 → 设置"}
	}
	st := d.GcodeState
	if st == "" {
		st = d.Stage
	}
	if !d.Printing && st == "" {
		st = "空闲"
	}
	conn := "未连接"
	if d.Connected {
		conn = "已连接"
	}
	boost := "关"
	if fmtAny(d.PrintBoostActive) == "是" {
		boost = "开"
	}
	lines := []string{
		"PandaSpool 机台 + 空气",
		"连接    " + conn,
		"状态    " + orDash(st),
		"打印    " + boolCN(d.Printing),
		fmt.Sprintf("进度    %.0f%%", d.Progress),
		"完成    " + orDash(d.ETA),
		fmt.Sprintf("剩余    %.0f 分钟", d.RemainingMin),
		"喷嘴    " + fmtAny(d.NozzleTemp) + " / " + fmtAny(d.NozzleTarget) + " ℃",
		"热床    " + fmtAny(d.BedTemp) + " / " + fmtAny(d.BedTarget) + " ℃",
		"层数    " + fmtAny(d.Layer) + " / " + fmtAny(d.TotalLayer),
		"任务    " + fmtAny(d.Job),
		"加强    " + boost,
		"结束于  " + fmtAny(d.PrintEndedAt),
		"更新    " + fmtAny(d.UpdatedAt),
		"PM1     " + fmtAny(d.PM1),
		"PM2.5   " + fmtAny(d.PM25),
		"PM10    " + fmtAny(d.PM10),
		"室温    " + fmtAny(d.TempC) + " ℃",
		"湿度    " + fmtAny(d.RH) + " %",
		"有人    " + fmtAny(d.Presence),
		"距离    " + fmtAny(d.DistanceCM) + " cm",
		"气区    " + fmtAny(d.AirZone),
		"气时    " + fmtUnix(d.AirTS),
	}
	if e := fmtAny(d.Error); e != "—" && e != "" {
		lines = append(lines, "错误    "+e)
	}
	return lines
}

func orDash(s string) string {
	if s == "" {
		return "—"
	}
	return s
}

func boolCN(v bool) string {
	if v {
		return "是"
	}
	return "否"
}

func hoverProc(hwnd windows.Handle, msg uint32, w, l uintptr) uintptr {
	if msg == WM_PAINT {
		var ps PAINTSTRUCT
		hdc, _, _ := procBeginPaint.Call(uintptr(hwnd), uintptr(unsafe.Pointer(&ps)))
		var rc RECT
		procGetClientRect.Call(uintptr(hwnd), uintptr(unsafe.Pointer(&rc)))
		br, _, _ := procCreateSolidBrush.Call(rgb(28, 32, 38))
		procFillRect.Call(hdc, uintptr(unsafe.Pointer(&rc)), br)
		procDeleteObject.Call(br)
		procSetBkMode.Call(hdc, TRANSPARENT)
		font, _, _ := procCreateFontW.Call(15, 0, 0, 0, 500, 0, 0, 0, 1, 0, 0, 5, 0, uintptr(unsafe.Pointer(utf16Ptr("Segoe UI"))))
		old, _, _ := procSelectObject.Call(hdc, font)
		lines := app.hoverLines()
		for i, line := range lines {
			if i == 0 {
				procSetTextColor.Call(hdc, rgb(61, 214, 198))
			} else {
				procSetTextColor.Call(hdc, rgb(236, 240, 244))
			}
			r := RECT{Left: 14, Top: int32(10 + i*20), Right: 326, Bottom: int32(30 + i*20)}
			u, _ := windows.UTF16FromString(line)
			procDrawTextW.Call(hdc, uintptr(unsafe.Pointer(&u[0])), uintptr(len(u)-1), uintptr(unsafe.Pointer(&r)), DT_LEFT|DT_WORDBREAK)
		}
		procSelectObject.Call(hdc, old)
		procDeleteObject.Call(font)
		procEndPaint.Call(uintptr(hwnd), uintptr(unsafe.Pointer(&ps)))
		return 0
	}
	if msg == WM_LBUTTONUP {
		app.openSettings()
		return 0
	}
	r, _, _ := procDefWindowProcW.Call(uintptr(hwnd), uintptr(msg), w, l)
	return r
}

func (a *App) openSettings() {
	if a.settings != 0 && visible(a.settings) {
		procSetForegroundWindow.Call(uintptr(a.settings))
		return
	}
	hwnd, _, _ := procCreateWindowExW.Call(
		0,
		uintptr(unsafe.Pointer(utf16Ptr("PPDeskSettings"))),
		uintptr(unsafe.Pointer(utf16Ptr("PandaSpool 设置"))),
		uintptr(WS_CAPTION|WS_SYSMENU|WS_VISIBLE),
		220, 180, 420, 230,
		0, 0, uintptr(a.inst), 0,
	)
	a.settings = windows.Handle(hwnd)
	procSetForegroundWindow.Call(hwnd)
}

func settingsProc(hwnd windows.Handle, msg uint32, w, l uintptr) uintptr {
	switch msg {
	case 0x0001: // WM_CREATE
		app.buildSettings(hwnd)
		return 0
	case WM_COMMAND:
		switch loWord(w) {
		case ID_SAVE:
			app.collectSettings(hwnd)
			_ = app.cfg.save()
			app.refresh()
			procDestroyWindow.Call(uintptr(hwnd))
		}
		return 0
	case WM_CLOSE:
		procDestroyWindow.Call(uintptr(hwnd))
		return 0
	case WM_DESTROY:
		app.settings = 0
		return 0
	}
	r, _, _ := procDefWindowProcW.Call(uintptr(hwnd), uintptr(msg), w, l)
	return r
}

func (a *App) buildSettings(hwnd windows.Handle) {
	url, token, _, _ := a.cfg.snapshot()
	createChild := func(class, text string, ex, style, x, y, w, h, id int) windows.Handle {
		r, _, _ := procCreateWindowExW.Call(
			uintptr(ex), uintptr(unsafe.Pointer(utf16Ptr(class))), uintptr(unsafe.Pointer(utf16Ptr(text))),
			uintptr(WS_CHILD|WS_VISIBLE|style),
			uintptr(x), uintptr(y), uintptr(w), uintptr(h),
			uintptr(hwnd), uintptr(id), uintptr(a.inst), 0,
		)
		return windows.Handle(r)
	}
	createChild("STATIC", "网址", 0, SS_LEFT, 20, 16, 360, 20, 0)
	createChild("EDIT", url, WS_EX_CLIENTEDGE, WS_TABSTOP|ES_AUTOHSCROLL, 20, 38, 360, 24, ID_URL)
	createChild("STATIC", "令牌（设置页 AI 令牌）", 0, SS_LEFT, 20, 72, 360, 20, 0)
	createChild("EDIT", token, WS_EX_CLIENTEDGE, WS_TABSTOP|ES_AUTOHSCROLL|ES_PASSWORD, 20, 94, 360, 24, ID_TOK)
	createChild("BUTTON", "保存", 0, WS_TABSTOP|BS_PUSHBUTTON, 20, 140, 90, 28, ID_SAVE)
}

func (a *App) collectSettings(hwnd windows.Handle) {
	urlH, _, _ := procGetDlgItem.Call(uintptr(hwnd), ID_URL)
	tokH, _, _ := procGetDlgItem.Call(uintptr(hwnd), ID_TOK)
	// GetDlgItem only works if we used dialog IDs as hMenu - we did.
	a.cfg.mu.Lock()
	a.cfg.URL = strings.TrimRight(getWindowText(windows.Handle(urlH)), "/")
	a.cfg.Token = getWindowText(windows.Handle(tokH))
	a.cfg.mu.Unlock()
}

func visible(h windows.Handle) bool {
	if h == 0 {
		return false
	}
	r, _, _ := procIsWindowVisible.Call(uintptr(h))
	return r != 0
}

func rgb(r, g, b uintptr) uintptr { return r | g<<8 | b<<16 }

func copyUTF16(dst []uint16, s string) {
	u, _ := windows.UTF16FromString(s)
	n := len(u)
	if n > len(dst) {
		n = len(dst)
	}
	copy(dst, u[:n])
}

func main() {
	app = &App{cfg: loadConfig()}
	if err := app.run(); err != nil {
		panic(err)
	}
}
