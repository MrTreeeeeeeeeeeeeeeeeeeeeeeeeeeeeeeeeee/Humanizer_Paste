#Requires AutoHotkey v2.0
#SingleInstance Force

; ==============================================================================
; KeyMimic v4.1 (AHK Edition - Enhanced UI)
; ==============================================================================

ConfigWithExtension := A_ScriptName . ".ini"
ConfigFile := StrReplace(ConfigWithExtension, ".ahk.ini", "_Settings.ini")

; === Preset Definitions ===
Presets := Map()

; Preset speeds are calibrated to the calculator using:
; seconds per character ≈ Speed + HoldTime/1000
; WPM ≈ (60 / secondsPerChar) / 5

Presets["Human"] := Map(
    "Speed",
    "0.065",
    "Var",
    "0.030",
    "HoldTime",
    "55",
    "PauseChance",
    "0.020",
    "PauseMin",
    "0.500",
    "PauseMax",
    "2.500",
    "BreakChance",
    "0.350",
    "BreakMin",
    "3.000",
    "BreakMax",
    "8.000",
    "MistakeChance",
    "0.060",
    "Description",
    "Natural typist around 100 WPM"
)

Presets["Super Human"] := Map(
    "Speed",
    "0.018",
    "Var",
    "0.009",
    "HoldTime",
    "30",
    "PauseChance",
    "0.010",
    "PauseMin",
    "0.300",
    "PauseMax",
    "1.500",
    "BreakChance",
    "0.200",
    "BreakMin",
    "1.500",
    "BreakMax",
    "4.000",
    "MistakeChance",
    "0.030",
    "Description",
    "Very fast typist around 250 WPM"
)

Presets["Extreme Human"] := Map(
    "Speed",
    "0.0067",
    "Var",
    "0.0030",
    "HoldTime",
    "20",
    "PauseChance",
    "0.005",
    "PauseMin",
    "0.200",
    "PauseMax",
    "0.800",
    "BreakChance",
    "0.100",
    "BreakMin",
    "1.000",
    "BreakMax",
    "2.500",
    "MistakeChance",
    "0.015",
    "Description",
    "Extremely fast typist around 450 WPM"
)

Presets["Super Extreme Human"] := Map(
    "Speed",
    "0.0065",
    "Var",
    "0.0030",
    "HoldTime",
    "12",
    "PauseChance",
    "0.002",
    "PauseMin",
    "0.100",
    "PauseMax",
    "0.400",
    "BreakChance",
    "0.050",
    "BreakMin",
    "0.500",
    "BreakMax",
    "1.500",
    "MistakeChance",
    "0.008",
    "Description",
    "Near max speed around 650 WPM"
)

Loop 2 {
    name := "Custom " . A_Index
    section := StrReplace(name, " ", "")
    Presets[name] := Map(
        "Speed",
        IniRead(ConfigFile, section, "Speed", "0.060"),
        "Var",
        IniRead(ConfigFile, section, "Var", "0.035"),
        "HoldTime",
        IniRead(ConfigFile, section, "HoldTime", "50"),
        "PauseChance",
        IniRead(ConfigFile, section, "PauseChance", "0.020"),
        "PauseMin",
        IniRead(ConfigFile, section, "PauseMin", "0.500"),
        "PauseMax",
        IniRead(ConfigFile, section, "PauseMax", "2.500"),
        "BreakChance",
        IniRead(ConfigFile, section, "BreakChance", "0.350"),
        "BreakMin",
        IniRead(ConfigFile, section, "BreakMin", "3.000"),
        "BreakMax",
        IniRead(ConfigFile, section, "BreakMax", "8.000"),
        "MistakeChance",
        IniRead(ConfigFile, section, "MistakeChance", "0.060"),
        "Description",
        "Your custom configuration"
    )
}

; === Create Main GUI ===
MyGui := Gui(, "KeyMimic v4.1 - Human Typing Simulator")
MyGui.SetFont("s9", "Segoe UI")
MyGui.OnEvent("Close", SaveAndExit)
MyGui.BackColor := "0xF0F0F0"

; === Header Section ===
MyGui.SetFont("s11 Bold")
MyGui.Add(
    "Text",
    "x20 y15 w500 Center",
    "⌨️ KeyMimic - Hardware-Level Typing Simulator"
)
MyGui.SetFont("s9")

; === Quick Start Panel ===
MyGui.Add("GroupBox", "x10 y45 w520 h120", "⚡ Quick Start")
MyGui.SetFont("s9 Bold")
MyGui.Add("Text", "x20 y65 w500", "Step 1: Choose Your Typing Style")
MyGui.SetFont("s9")

LastPreset := IniRead(ConfigFile, "Settings", "LastPreset", "Human")
presetList := [
    "Human",
    "Super Human",
    "Extreme Human",
    "Super Extreme Human",
    "Custom 1",
    "Custom 2",
]
ddPreset := MyGui.Add(
    "DropDownList",
    "x20 y85 w300 vPresetChoice",
    presetList
)
ddPreset.Text := LastPreset
ddPreset.OnEvent("Change", LoadPreset)

; Scrollable, wrapped, no horizontal scroll bar
txtPresetDesc := MyGui.Add(
    "Edit",
    "x20 y112 w300 r2 +ReadOnly +VScroll -TabStop",
    ""
)
txtPresetDesc.SetFont("cGray")
UpdatePresetDescription(LastPreset)

MyGui.SetFont("s9 Bold")
MyGui.Add("Text", "x330 y65 w190", "Step 2: Set Hotkey")
MyGui.SetFont("s9")
DefaultHK := IniRead(ConfigFile, "Settings", "Hotkey", "^+!v")
hkControl := MyGui.Add("Hotkey", "x330 y85 w180 vUserHotkey", DefaultHK)
hkControl.OnEvent("Change", UpdateHotkey)
MyGui.SetFont("s8 cGray")
MyGui.Add("Text", "x330 y108 w180", "Default: Ctrl+Shift+Alt+V")
MyGui.SetFont("s9")

MyGui.Add(
    "Text",
    "x330 y125 w180 h30 cGreen",
    "✓ Copy text to clipboard`n✓ Press hotkey to type"
)

; === Tab Control for Advanced Settings ===
MyGui.SetFont("s9")
TabCtrl := MyGui.Add("Tab3", "x10 y175 w520 h330", ["⚡ Speed", "⏸️ Pauses", "🎯 Realism"])

; ========== TAB 1: SPEED ==========
TabCtrl.UseTab(1)

MyGui.Add("GroupBox", "x20 y205 w500 h110", "Typing Speed Settings")

MyGui.Add("Text", "x30 y225 w240", "Base Speed (seconds per character):")
MyGui.Add("Edit", "x280 y223 w80 h22 vSpeed")
MyGui.Add("Text", "x370 y225 w130 cNavy", "Lower = Faster")

MyGui.Add("Text", "x30 y255 w240", "Speed Variation (+/- seconds):")
MyGui.Add("Edit", "x280 y253 w80 h22 vVar")
MyGui.Add("Text", "x370 y255 w130 cNavy", "Adds randomness")

MyGui.Add("Text", "x30 y285 w240", "Key Hold Duration (milliseconds):")
MyGui.Add("Edit", "x280 y283 w80 h22 vHoldTime")
MyGui.Add("UpDown", "Range5-200", 50)
MyGui.Add("Text", "x370 y285 w130 cNavy", "Physical key press")

MyGui.Add("GroupBox", "x20 y325 w500 h165", "Speed Calculator & Preview")

MyGui.SetFont("s10 Bold")
MyGui.Add("Text", "x30 y350 w200", "Typing Speed Estimate:")
MyGui.SetFont("s9")

; Scrollable, wrapped, no horizontal scroll bar
txtSpeedCalc := MyGui.Add(
    "Edit",
    "x30 y370 w470 r6 +ReadOnly +VScroll -TabStop",
    ""
)
txtSpeedCalc.SetFont("cGreen")

; ========== TAB 2: PAUSES ==========
TabCtrl.UseTab(2)

MyGui.Add("GroupBox", "x20 y205 w500 h135", "💭 Thinking Pauses (Mid-Sentence)")
MyGui.SetFont("s8 cGray")
MyGui.Add(
    "Text",
    "x30 y222 w460",
    "Random hesitations while typing, like when you pause to think of the next word"
)
MyGui.SetFont("s9 cDefault")

MyGui.Add("Text", "x30 y245 w230", "Frequency (0 = never, 1 = always):")
MyGui.Add("Edit", "x270 y243 w80 h22 vPauseChance")
MyGui.Add("Text", "x360 y245 w140 cNavy", "0.02 = 2% chance per char")

MyGui.Add("Text", "x30 y275 w230", "Minimum Duration (seconds):")
MyGui.Add("Edit", "x270 y273 w80 h22 vPauseMin")
MyGui.Add("Text", "x30 y305 w230", "Maximum Duration (seconds):")
MyGui.Add("Edit", "x270 y303 w80 h22 vPauseMax")

MyGui.Add("GroupBox", "x20 y350 w500 h140", "⏎ Line Breaks (After Enter Key)")
MyGui.SetFont("s8 cGray")
MyGui.Add(
    "Text",
    "x30 y367 w460",
    "Longer pauses after hitting Enter, like taking a breath between paragraphs"
)
MyGui.SetFont("s9 cDefault")

MyGui.Add("Text", "x30 y390 w230", "Frequency (0 = never, 1 = always):")
MyGui.Add("Edit", "x270 y388 w80 h22 vBreakChance")
MyGui.Add("Text", "x360 y390 w140 cNavy", "0.35 = 35% chance")

MyGui.Add("Text", "x30 y420 w230", "Minimum Duration (seconds):")
MyGui.Add("Edit", "x270 y418 w80 h22 vBreakMin")
MyGui.Add("Text", "x30 y450 w230", "Maximum Duration (seconds):")
MyGui.Add("Edit", "x270 y448 w80 h22 vBreakMax")

; ========== TAB 3: REALISM ==========
TabCtrl.UseTab(3)

MyGui.Add("GroupBox", "x20 y205 w500 h145", "❌ Typing Mistakes")
MyGui.SetFont("s8 cGray")
MyGui.Add(
    "Text",
    "x30 y222 w460",
    "Simulates typos by typing a wrong character then backspacing to correct it"
)
MyGui.SetFont("s9 cDefault")

MyGui.Add("Text", "x30 y245 w230", "Mistake Rate (0 = perfect typing):")
MyGui.Add("Edit", "x270 y243 w80 h22 vMistakeChance")
MyGui.Add("Text", "x360 y245 w140 cNavy", "0.06 = ~1 per 17 chars")

MyGui.Add("GroupBox", "x20 y360 w500 h130", "ℹ️ How It Works")

; Scrollable, wrapped, no horizontal scroll bar
txtRealismInfo := MyGui.Add(
    "Edit",
    "x30 y380 w470 r5 +ReadOnly +VScroll -TabStop",
    "✓ This tool uses hardware-level scan codes`r`n"
        . "Keystrokes are sent via the Windows SendInput API with KEYEVENTF_SCANCODE flags. "
        . "This makes every keystroke appear as if it's coming from a physical keyboard at the driver level.`r`n`r`n"
        . "1. Copy your text to the clipboard`r`n"
        . "2. Click in the target application window`r`n"
        . "3. Press your configured hotkey`r`n"
        . "4. KeyMimic will type the text character by character`r`n`r`n"
        . "Each keystroke includes:`r`n"
        . "Down press → Random hold time → Up release`r`n"
        . "Shift handling for uppercase and symbols`r`n"
        . "Random timing variations and pauses"
)
txtRealismInfo.SetFont("cGreen")

TabCtrl.UseTab()

; === Action Buttons ===
MyGui.SetFont("s9 Bold")
btnApply := MyGui.Add("Button", "x10 y515 w165 h35 Default", "💾 Apply Preset")
btnApply.OnEvent("Click", (*) => ApplyPresetToFields(MyGui["PresetChoice"].Text))

btnSaveCustom := MyGui.Add("Button", "x185 y515 w165 h35", "📝 Save to Custom Slot")
btnSaveCustom.OnEvent("Click", SaveToCustom)

btnSave := MyGui.Add("Button", "x360 y515 w170 h35", "✓ Save & Close")
btnSave.OnEvent("Click", SaveAndExit)

; === Status Bar ===
MyGui.SetFont("s8")
MyGui.Add(
    "Text",
    "x10 y560 w520 h25 Center BackgroundF8F8F8 Border",
    "🛑 Press ESC anytime during typing to emergency stop  •  Status: Ready"
)
global StatusText := MyGui.Add(
    "Text",
    "x10 y590 w520 Center cGray",
    "Waiting for hotkey press..."
)

; Live update the calculator when the relevant fields change
MyGui["Speed"].OnEvent("Change", UpdateSpeedCalculator)
MyGui["Var"].OnEvent("Change", UpdateSpeedCalculator)
MyGui["HoldTime"].OnEvent("Change", UpdateSpeedCalculator)
MyGui["PauseChance"].OnEvent("Change", UpdateSpeedCalculator)
MyGui["PauseMin"].OnEvent("Change", UpdateSpeedCalculator)
MyGui["PauseMax"].OnEvent("Change", UpdateSpeedCalculator)

MyGui.Show("w540 h620")

; Load initial values
ApplyPresetToFields(LastPreset)

; Register Hotkey
CurrentHotkey := DefaultHK
if (CurrentHotkey != "") {
    try {
        Hotkey(CurrentHotkey, StartProcess)
    } catch {
        MsgBox("Failed to register hotkey: " CurrentHotkey, "Error", 16)
    }
}

; ==============================================================================
; UI Helper Functions
; ==============================================================================

UpdatePresetDescription(presetName)
{
    global Presets, txtPresetDesc
    if Presets.Has(presetName)
        txtPresetDesc.Value := Presets[presetName]["Description"]
}

UpdateSpeedCalculator(*)
{
    global txtSpeedCalc, MyGui

    try {
        Saved := MyGui.Submit(false)

        speed := Float(Saved.Speed)
        var := Float(Saved.Var)
        holdMs := Integer(Saved.HoldTime)

        pauseChance := Float(Saved.PauseChance)
        pauseMin := Float(Saved.PauseMin)
        pauseMax := Float(Saved.PauseMax)

        holdSec := holdMs / 1000.0

        minDelay := speed - var
        if (minDelay < 0.001)
            minDelay := 0.001

        maxDelay := speed + var
        if (maxDelay < 0.001)
            maxDelay := 0.001

        secPerCharMin := holdSec + minDelay
        secPerCharAvg := holdSec + speed
        secPerCharMax := holdSec + maxDelay

        cpmAvg := Round(60 / secPerCharAvg)
        wpmAvg := Round(cpmAvg / 5)

        wpmMin := Round((60 / secPerCharMax) / 5)
        wpmMax := Round((60 / secPerCharMin) / 5)

        timeFor100 := Round(secPerCharAvg * 100, 1)

        avgPause := (pauseMin + pauseMax) / 2.0
        secPerCharWithPauses := secPerCharAvg + (pauseChance * avgPause)
        wpmWithPauses := Round((60 / secPerCharWithPauses) / 5)

        calcText := "Estimated speed (includes hold time):`r`n"
        calcText .= "Words per minute: ~" wpmAvg " WPM (range ~" wpmMin " to " wpmMax ")`r`n"
        calcText .= "Characters per minute: ~" cpmAvg " CPM`r`n"
        calcText .= "Time to type 100 characters: ~" timeFor100 " seconds`r`n`r`n"
        calcText .= "Including thinking pauses (not Enter breaks): ~" wpmWithPauses " WPM`r`n`r`n"

        if (wpmAvg < 30)
            calcText .= "Very slow (learning typist)"
        else if (wpmAvg < 60)
            calcText .= "Realistic (average typist)"
        else if (wpmAvg < 120)
            calcText .= "Fast (skilled typist)"
        else
            calcText .= "Very fast (expert level)"

        txtSpeedCalc.Value := calcText
    }
}

; ==============================================================================
; Preset Management
; ==============================================================================

LoadPreset(ctrl, *)
{
    UpdatePresetDescription(ctrl.Text)
    ApplyPresetToFields(ctrl.Text)
}

ApplyPresetToFields(presetName)
{
    global Presets, MyGui, StatusText
    if !Presets.Has(presetName)
        return

    p := Presets[presetName]
    MyGui["Speed"].Value := p["Speed"]
    MyGui["Var"].Value := p["Var"]
    MyGui["HoldTime"].Value := p["HoldTime"]
    MyGui["PauseChance"].Value := p["PauseChance"]
    MyGui["PauseMin"].Value := p["PauseMin"]
    MyGui["PauseMax"].Value := p["PauseMax"]
    MyGui["BreakChance"].Value := p["BreakChance"]
    MyGui["BreakMin"].Value := p["BreakMin"]
    MyGui["BreakMax"].Value := p["BreakMax"]
    MyGui["MistakeChance"].Value := p["MistakeChance"]

    UpdateSpeedCalculator()

    StatusText.Value := "✓ Loaded preset: " presetName
    StatusText.SetFont("cGreen")
    SetTimer(
        () => (StatusText.Value := "Waiting for hotkey press...", StatusText.SetFont("cGray")),
        -3000
    )
}

SaveToCustom(*)
{
    global Presets, MyGui, ConfigFile, StatusText

    result := MsgBox(
        "Which custom slot would you like to save to?`n`nYes = Custom 1`nNo = Custom 2`nCancel = Don't Save",
        "Save Custom Preset",
        "YesNoCancel Icon?"
    )

    if (result = "Cancel")
        return

    choice := (result = "Yes") ? "Custom 1" : "Custom 2"
    section := StrReplace(choice, " ", "")
    Saved := MyGui.Submit(false)

    fieldMap := Map(
        "Speed",
        Saved.Speed,
        "Var",
        Saved.Var,
        "HoldTime",
        Saved.HoldTime,
        "PauseChance",
        Saved.PauseChance,
        "PauseMin",
        Saved.PauseMin,
        "PauseMax",
        Saved.PauseMax,
        "BreakChance",
        Saved.BreakChance,
        "BreakMin",
        Saved.BreakMin,
        "BreakMax",
        Saved.BreakMax,
        "MistakeChance",
        Saved.MistakeChance
    )

    for key, val in fieldMap
        IniWrite(val, ConfigFile, section, key)

    fieldMap["Description"] := "Your custom configuration"
    Presets[choice] := fieldMap

    StatusText.Value := "✓ Saved to " choice
    StatusText.SetFont("cGreen")
    SetTimer(
        () => (StatusText.Value := "Waiting for hotkey press...", StatusText.SetFont("cGray")),
        -3000
    )
}

; ==============================================================================
; Save Functions
; ==============================================================================

SaveAndExit(*)
{
    global MyGui
    Saved := MyGui.Submit(false)
    WriteIni(Saved)
    ExitApp()
}

WriteIni(Saved)
{
    global ConfigFile
    IniWrite(Saved.UserHotkey, ConfigFile, "Settings", "Hotkey")
    IniWrite(Saved.PresetChoice, ConfigFile, "Settings", "LastPreset")
}

; ==============================================================================
; Hotkey Management
; ==============================================================================
UpdateHotkey(*)
{
    global CurrentHotkey, StatusText, MyGui
    Saved := MyGui.Submit(false)
    NewKey := Saved.UserHotkey

    if (NewKey == "")
        return

    try {
        if (CurrentHotkey != "")
            Hotkey(CurrentHotkey, "Off")

        Hotkey(NewKey, StartProcess)
        CurrentHotkey := NewKey
        Hotkey(NewKey, "On")

        StatusText.Value := "✓ Hotkey updated: " NewKey
        StatusText.SetFont("cGreen")
        SetTimer(
            () => (StatusText.Value := "Waiting for hotkey press...", StatusText.SetFont("cGray")),
            -3000
        )
    } catch as e {
        MsgBox("Failed to set hotkey: " e.Message, "Error", 16)
    }
}

; ==============================================================================
; Main Typing Process
; ==============================================================================
StartProcess(*)
{
    global StatusText, MyGui

    ToolTip()

    if (A_Clipboard = "") {
        StatusText.Value := "❌ Error: Clipboard is empty!"
        StatusText.SetFont("cRed")
        SetTimer(
            () => (StatusText.Value := "Waiting for hotkey press...", StatusText.SetFont("cGray")),
            -3000
        )
        return
    }

    textToType := A_Clipboard
    charCount := StrLen(textToType)
    Saved := MyGui.Submit(false)

    try {
        cfg := Object()
        cfg.Speed := Float(Saved.Speed)
        cfg.Var := Float(Saved.Var)
        cfg.HoldTime := Integer(Saved.HoldTime)
        cfg.PauseChance := Float(Saved.PauseChance)
        cfg.PauseMin := Float(Saved.PauseMin)
        cfg.PauseMax := Float(Saved.PauseMax)
        cfg.BreakChance := Float(Saved.BreakChance)
        cfg.BreakMin := Float(Saved.BreakMin)
        cfg.BreakMax := Float(Saved.BreakMax)
        cfg.Mistake := Float(Saved.MistakeChance)
    } catch {
        StatusText.Value := "❌ Error: Invalid numeric values in settings"
        StatusText.SetFont("cRed")
        SetTimer(
            () => (StatusText.Value := "Waiting for hotkey press...", StatusText.SetFont("cGray")),
            -3000
        )
        return
    }

    estimatedTime := Round((cfg.Speed + (cfg.HoldTime / 1000.0)) * charCount)

    countdown := 5
    StatusText.Value := "⏳ Starting in " countdown " seconds... (" charCount " chars, ~" estimatedTime "s)"
    StatusText.SetFont("cBlue")

    Loop countdown {
        secsLeft := countdown - A_Index + 1
        ToolTip("KeyMimic`nStarting in " secsLeft " seconds...`nPress ESC to stop")
        Sleep(1000)
    }
    ToolTip()

    StatusText.Value := "⌨️ Typing in progress... (Press ESC to stop)"
    StatusText.SetFont("s8 cGreen Bold")
    ToolTip("KeyMimic`nTyping in progress...`nPress ESC to stop")

    TypeHuman(textToType, cfg)

    ToolTip()

    StatusText.Value := "✓ Completed! Typed " charCount " characters"
    StatusText.SetFont("cGreen")

    MsgBox(
        "✓ Typing completed successfully!`n`nCharacters typed: " charCount,
        "KeyMimic",
        64
    )

    SetTimer(
        () => (StatusText.Value := "Waiting for hotkey press...", StatusText.SetFont("s8 cGray")),
        -5000
    )
}

; ==============================================================================
; Hardware Scan Code Functions
; ==============================================================================

SendScanInput(scanCode, flags)
{
    inputSize := A_PtrSize = 8 ? 40 : 28
    buf := Buffer(inputSize, 0)
    NumPut("UInt", 1, buf, 0)
    kbOffset := A_PtrSize = 8 ? 8 : 4
    NumPut("UShort", 0, buf, kbOffset)
    NumPut("UShort", scanCode, buf, kbOffset + 2)
    NumPut("UInt", 0x0008 | flags, buf, kbOffset + 4)
    NumPut("UInt", 0, buf, kbOffset + 8)
    NumPut("UPtr", 0, buf, kbOffset + 12)
    DllCall("SendInput", "UInt", 1, "Ptr", buf.Ptr, "Int", inputSize)
}

PressKeyScan(scanCode, holdTime, isExtended := false)
{
    extFlag := isExtended ? 0x0001 : 0
    SendScanInput(scanCode, extFlag)
    actualHold := Random(holdTime - 10, holdTime + 10)
    if (actualHold < 5)
        actualHold := 5
    Sleep(actualHold)
    SendScanInput(scanCode, extFlag | 0x0002)
}

CharToScanInfo(char)
{
    info := Object()
    info.vk := 0
    info.scan := 0
    info.needShift := false
    info.needCtrlAlt := false

    result := DllCall("VkKeyScanW", "UShort", Ord(char), "Short")
    if (result = -1)
        return info

    vk := result & 0xFF
    shiftState := (result >> 8) & 0xFF
    info.vk := vk
    info.scan := DllCall("MapVirtualKeyW", "UInt", vk, "UInt", 0, "UInt")
    info.needShift := (shiftState & 1) ? true : false
    info.needCtrlAlt := (shiftState & 6) ? true : false
    return info
}

SendCharHW(char, holdTime)
{
    info := CharToScanInfo(char)
    if (info.scan = 0)
        return false

    static SC_LSHIFT := 0x2A
    static SC_LCTRL := 0x1D
    static SC_LALT := 0x38

    if (info.needCtrlAlt) {
        SendScanInput(SC_LCTRL, 0)
        Sleep(Random(5, 15))
        SendScanInput(SC_LALT, 0)
        Sleep(Random(5, 15))
    }
    if (info.needShift) {
        SendScanInput(SC_LSHIFT, 0)
        Sleep(Random(5, 15))
    }

    PressKeyScan(info.scan, holdTime)

    if (info.needShift) {
        Sleep(Random(5, 15))
        SendScanInput(SC_LSHIFT, 0x0002)
    }
    if (info.needCtrlAlt) {
        Sleep(Random(5, 15))
        SendScanInput(SC_LALT, 0x0002)
        Sleep(Random(5, 15))
        SendScanInput(SC_LCTRL, 0x0002)
    }
    return true
}

; ==============================================================================
; Typing Logic
; ==============================================================================

TypeHuman(str, cfg)
{
    static SC_ENTER := 0x1C
    static SC_BACKSPACE := 0x0E
    static SC_SPACE := 0x39
    static SC_TAB := 0x0F

    Loop Parse, str {
        char := A_LoopField

        if (Random() < cfg.Mistake) {
            wrongChar := Chr(Random(97, 122))
            SendCharHW(wrongChar, cfg.HoldTime)
            HumanDelay(cfg.Speed, cfg.Var)
            PressKeyScan(SC_BACKSPACE, cfg.HoldTime)
            HumanDelay(cfg.Speed, cfg.Var)
        }

        if (char = "`r")
            continue

        if (char = "`n") {
            PressKeyScan(SC_ENTER, cfg.HoldTime)
        } else if (char = " ") {
            PressKeyScan(SC_SPACE, cfg.HoldTime)
        } else if (char = "`t") {
            PressKeyScan(SC_TAB, cfg.HoldTime)
        } else {
            if (!SendCharHW(char, cfg.HoldTime))
                SendEvent("{Text}" . char)
        }

        HumanDelay(cfg.Speed, cfg.Var)

        if (char = "`n" or char = "`r") {
            if (Random() < cfg.BreakChance) {
                wait := Random(cfg.BreakMin, cfg.BreakMax) * 1000
                Sleep(wait)
            }
        } else if (Random() < cfg.PauseChance) {
            wait := Random(cfg.PauseMin, cfg.PauseMax) * 1000
            Sleep(wait)
        }
    }
}

HumanDelay(baseSpeed, variation)
{
    randomSeconds := Random(baseSpeed - variation, baseSpeed + variation)
    if (randomSeconds < 0.001)
        randomSeconds := 0.001
    Sleep(randomSeconds * 1000)
}

Escape::
{
    global StatusText
    ToolTip()
    StatusText.Value := "🛑 Emergency stop activated - Reloading..."
    StatusText.SetFont("s8 cRed Bold")
    Sleep(500)
    Reload()
}