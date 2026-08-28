package main

import (
	"image"
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	modUser32   = windows.NewLazySystemDLL("user32.dll")
	modGdi32    = windows.NewLazySystemDLL("gdi32.dll")
	modShell32  = windows.NewLazySystemDLL("shell32.dll")
	modKernel32 = windows.NewLazySystemDLL("kernel32.dll")

	procRegisterClassExW       = modUser32.NewProc("RegisterClassExW")
	procCreateWindowExW        = modUser32.NewProc("CreateWindowExW")
	procDefWindowProcW         = modUser32.NewProc("DefWindowProcW")
	procGetMessageW            = modUser32.NewProc("GetMessageW")
	procTranslateMessage       = modUser32.NewProc("TranslateMessage")
	procDispatchMessageW       = modUser32.NewProc("DispatchMessageW")
	procPostQuitMessage        = modUser32.NewProc("PostQuitMessage")
	procShowWindow             = modUser32.NewProc("ShowWindow")
	procUpdateWindow           = modUser32.NewProc("UpdateWindow")
	procDestroyWindow          = modUser32.NewProc("DestroyWindow")
	procSetWindowTextW         = modUser32.NewProc("SetWindowTextW")
	procGetWindowTextW         = modUser32.NewProc("GetWindowTextW")
	procGetWindowTextLengthW   = modUser32.NewProc("GetWindowTextLengthW")
	procSetTimer               = modUser32.NewProc("SetTimer")
	procKillTimer              = modUser32.NewProc("KillTimer")
	procGetCursorPos           = modUser32.NewProc("GetCursorPos")
	procSetWindowPos           = modUser32.NewProc("SetWindowPos")
	procInvalidateRect         = modUser32.NewProc("InvalidateRect")
	procGetClientRect          = modUser32.NewProc("GetClientRect")
	procBeginPaint             = modUser32.NewProc("BeginPaint")
	procEndPaint               = modUser32.NewProc("EndPaint")
	procFillRect               = modUser32.NewProc("FillRect")
	procDrawTextW              = modUser32.NewProc("DrawTextW")
	procSetBkMode              = modGdi32.NewProc("SetBkMode")
	procSetTextColor           = modGdi32.NewProc("SetTextColor")
	procCreateSolidBrush       = modGdi32.NewProc("CreateSolidBrush")
	procDeleteObject           = modGdi32.NewProc("DeleteObject")
	procSelectObject           = modGdi32.NewProc("SelectObject")
	procCreateFontW            = modGdi32.NewProc("CreateFontW")
	procSendMessageW           = modUser32.NewProc("SendMessageW")
	procGetDlgItem             = modUser32.NewProc("GetDlgItem")
	procDestroyIcon            = modUser32.NewProc("DestroyIcon")
	procGetDC                  = modUser32.NewProc("GetDC")
	procReleaseDC              = modUser32.NewProc("ReleaseDC")
	procCreateDIBSection       = modGdi32.NewProc("CreateDIBSection")
	procCreateBitmap           = modGdi32.NewProc("CreateBitmap")
	procCreateIconIndirect     = modUser32.NewProc("CreateIconIndirect")
	procShell_NotifyIconW      = modShell32.NewProc("Shell_NotifyIconW")
	procShell_NotifyIconGetRect = modShell32.NewProc("Shell_NotifyIconGetRect")
	procGetModuleHandleW       = modKernel32.NewProc("GetModuleHandleW")
	procLoadCursorW            = modUser32.NewProc("LoadCursorW")
	procMoveWindow             = modUser32.NewProc("MoveWindow")
	procGetWindowRect          = modUser32.NewProc("GetWindowRect")
	procPtInRect               = modUser32.NewProc("PtInRect")
	procSetForegroundWindow    = modUser32.NewProc("SetForegroundWindow")
	procIsWindowVisible        = modUser32.NewProc("IsWindowVisible")
	procCreatePopupMenu        = modUser32.NewProc("CreatePopupMenu")
	procAppendMenuW            = modUser32.NewProc("AppendMenuW")
	procTrackPopupMenu         = modUser32.NewProc("TrackPopupMenu")
	procDestroyMenu            = modUser32.NewProc("DestroyMenu")
	procPostMessageW           = modUser32.NewProc("PostMessageW")
)

const (
	WM_DESTROY       = 0x0002
	WM_CLOSE         = 0x0010
	WM_COMMAND       = 0x0111
	WM_PAINT         = 0x000F
	WM_TIMER         = 0x0113
	WM_CONTEXTMENU   = 0x007B
	WM_LBUTTONUP     = 0x0202
	WM_RBUTTONUP     = 0x0205
	WM_RBUTTONDOWN   = 0x0204
	WM_NULL          = 0x0000
	WM_MOUSEMOVE     = 0x0200
	WM_MOUSELEAVE    = 0x02A3
	WM_APP           = 0x8000
	WM_USER          = 0x0400
	WM_TRAY          = WM_APP + 1
	WM_NCACTIVATE    = 0x0086

	NIN_SELECT     = WM_USER + 0
	NIN_KEYSELECT  = WM_USER + 1
	NIN_POPUPOPEN  = WM_USER + 6
	NIN_POPUPCLOSE = WM_USER + 7

	NIM_ADD        = 0
	NIM_MODIFY     = 1
	NIM_DELETE     = 2
	NIM_SETVERSION = 4
	NIF_MESSAGE    = 0x01
	NIF_ICON       = 0x02
	NIF_TIP        = 0x04
	NIF_SHOWTIP    = 0x80
	NOTIFYICON_VERSION_4 = 4

	WS_OVERLAPPEDWINDOW = 0x00CF0000
	WS_POPUP            = 0x80000000
	WS_VISIBLE          = 0x10000000
	WS_CAPTION          = 0x00C00000
	WS_SYSMENU          = 0x00080000
	WS_CHILD            = 0x40000000
	WS_TABSTOP          = 0x00010000
	WS_AUTOCHECKBOX     = 0x00000003 // BS_AUTOCHECKBOX
	BS_PUSHBUTTON       = 0
	BS_AUTOCHECKBOX     = 3
	ES_AUTOHSCROLL      = 0x0080
	ES_PASSWORD         = 0x0020
	SS_LEFT             = 0

	WS_EX_TOPMOST     = 0x00000008
	WS_EX_TOOLWINDOW  = 0x00000080
	WS_EX_NOACTIVATE  = 0x08000000
	WS_EX_LAYERED     = 0x00080000
	WS_EX_CLIENTEDGE  = 0x00000200

	SW_HIDE    = 0
	SW_SHOWNA  = 8
	SW_SHOW    = 5
	SWP_NOSIZE = 0x0001
	SWP_NOZORDER = 0x0004
	SWP_NOACTIVATE = 0x0010
	SWP_SHOWWINDOW = 0x0040
	HWND_TOPMOST = ^windows.Handle(0) // -1

	IDC_ARROW     = 32512
	COLOR_WINDOW  = 5
	TRANSPARENT   = 1
	DT_LEFT       = 0
	DT_WORDBREAK  = 0x0010
	BM_GETCHECK   = 0x00F0
	BM_SETCHECK   = 0x00F1
	BST_CHECKED   = 1
	BST_UNCHECKED = 0
	DIB_RGB_COLORS = 0
	BI_RGB        = 0

	CS_HREDRAW = 0x0002
	CS_VREDRAW = 0x0001
	ID_SAVE = 1100
	ID_QUIT = 1101
	ID_URL  = 1001
	ID_TOK  = 1002
	ID_SHOW = 1020
	IDM_SETTINGS = 2001
	IDM_EXIT     = 2002

	MF_STRING       = 0x0000
	MF_SEPARATOR    = 0x0800
	TPM_RIGHTBUTTON = 0x0002
	TPM_RETURNCMD   = 0x0100
	TPM_BOTTOMALIGN = 0x0020
	TPM_RIGHTALIGN  = 0x0008
)

type WNDCLASSEX struct {
	CbSize        uint32
	Style         uint32
	LpfnWndProc   uintptr
	CbClsExtra    int32
	CbWndExtra    int32
	HInstance     windows.Handle
	HIcon         windows.Handle
	HCursor       windows.Handle
	HbrBackground windows.Handle
	LpszMenuName  *uint16
	LpszClassName *uint16
	HIconSm       windows.Handle
}

type POINT struct{ X, Y int32 }
type RECT struct{ Left, Top, Right, Bottom int32 }

type MSG struct {
	HWnd    windows.Handle
	Message uint32
	WParam  uintptr
	LParam  uintptr
	Time    uint32
	Pt      POINT
}

type PAINTSTRUCT struct {
	Hdc         windows.Handle
	FErase      int32
	RcPaint     RECT
	FRestore    int32
	FIncUpdate  int32
	RgbReserved [32]byte
}

type BITMAPINFOHEADER struct {
	BiSize          uint32
	BiWidth         int32
	BiHeight        int32
	BiPlanes        uint16
	BiBitCount      uint16
	BiCompression   uint32
	BiSizeImage     uint32
	BiXPelsPerMeter int32
	BiYPelsPerMeter int32
	BiClrUsed       uint32
	BiClrImportant  uint32
}

type BITMAPINFO struct {
	BmiHeader BITMAPINFOHEADER
	BmiColors [1]uint32
}

type ICONINFO struct {
	FIcon    int32
	XHotspot uint32
	YHotspot uint32
	HbmMask  windows.Handle
	HbmColor windows.Handle
}

type NOTIFYICONDATA struct {
	CbSize           uint32
	HWnd             windows.Handle
	UID              uint32
	UFlags           uint32
	UCallbackMessage uint32
	HIcon            windows.Handle
	SzTip            [128]uint16
	DwState          uint32
	DwStateMask      uint32
	SzInfo           [256]uint16
	UVersion         uint32
	SzInfoTitle      [64]uint16
	DwInfoFlags      uint32
	GUIDItem         windows.GUID
	HBalloonIcon     windows.Handle
}

type NOTIFYICONIDENTIFIER struct {
	CbSize uint32
	HWnd   windows.Handle
	UID    uint32
	GUID   windows.GUID
}

func loWord(v uintptr) uint16 { return uint16(v) }
func hiWord(v uintptr) uint16 { return uint16(v >> 16) }

func utf16Ptr(s string) *uint16 {
	p, _ := windows.UTF16PtrFromString(s)
	return p
}

func hiconFromRGBA(img *image.RGBA) windows.Handle {
	w, h := img.Bounds().Dx(), img.Bounds().Dy()
	var bi BITMAPINFO
	bi.BmiHeader.BiSize = 40
	bi.BmiHeader.BiWidth = int32(w)
	bi.BmiHeader.BiHeight = int32(-h)
	bi.BmiHeader.BiPlanes = 1
	bi.BmiHeader.BiBitCount = 32
	bi.BmiHeader.BiCompression = BI_RGB
	hdc, _, _ := procGetDC.Call(0)
	var bits unsafe.Pointer
	hbm, _, _ := procCreateDIBSection.Call(hdc, uintptr(unsafe.Pointer(&bi)), DIB_RGB_COLORS, uintptr(unsafe.Pointer(&bits)), 0, 0)
	procReleaseDC.Call(0, hdc)
	if hbm == 0 || bits == nil {
		return 0
	}
	dst := unsafe.Slice((*byte)(bits), w*h*4)
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			c := img.RGBAAt(x, y)
			i := (y*w + x) * 4
			a := float64(c.A) / 255
			dst[i+0] = byte(float64(c.B) * a)
			dst[i+1] = byte(float64(c.G) * a)
			dst[i+2] = byte(float64(c.R) * a)
			dst[i+3] = c.A
		}
	}
	mask, _, _ := procCreateBitmap.Call(uintptr(w), uintptr(h), 1, 1, 0)
	var ii ICONINFO
	ii.FIcon = 1
	ii.HbmMask = windows.Handle(mask)
	ii.HbmColor = windows.Handle(hbm)
	hicon, _, _ := procCreateIconIndirect.Call(uintptr(unsafe.Pointer(&ii)))
	procDeleteObject.Call(hbm)
	procDeleteObject.Call(mask)
	return windows.Handle(hicon)
}

func setWindowText(hwnd windows.Handle, s string) {
	procSetWindowTextW.Call(uintptr(hwnd), uintptr(unsafe.Pointer(utf16Ptr(s))))
}

func getWindowText(hwnd windows.Handle) string {
	n, _, _ := procGetWindowTextLengthW.Call(uintptr(hwnd))
	buf := make([]uint16, n+2)
	procGetWindowTextW.Call(uintptr(hwnd), uintptr(unsafe.Pointer(&buf[0])), n+1)
	return windows.UTF16ToString(buf)
}
