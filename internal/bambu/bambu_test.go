package bambu

import (
	"testing"
	"time"
)

func TestPrintingFromState(t *testing.T) {
	if !PrintingFromState("RUNNING", "idle") {
		t.Fatal("running")
	}
	if !PrintingFromState("PAUSE", "paused_user") {
		t.Fatal("pause still printing")
	}
	if PrintingFromState("FINISH", "printing") {
		t.Fatal("finish must win over leftover stage=printing")
	}
	if PrintingFromState("IDLE", "printing") {
		t.Fatal("idle")
	}
	if PrintingFromState("", "printing") {
		t.Fatal("leftover stage=printing without gcode must not keep boost on")
	}
	if !PrintingFromState("", "heatbed_preheating") {
		t.Fatal("live prep stage without gcode still counts")
	}
}

func TestPrintEndStartsBoostThenExpires(t *testing.T) {
	c := New()
	c.applyPrint(map[string]any{"gcode_state": "RUNNING", "mc_print_stage": float64(0)})
	if !c.PrintingOrBoost(30) {
		t.Fatal("should be on while running")
	}
	c.applyPrint(map[string]any{"gcode_state": "FINISH"})
	if !c.PrintingOrBoost(30) {
		t.Fatal("should stay on during boost window")
	}
	c.mu.Lock()
	c.printEnd = time.Now().Add(-31 * time.Minute)
	c.mu.Unlock()
	if c.PrintingOrBoost(30) {
		t.Fatal("should be off after 30 minutes")
	}
}

func TestFirstSnapshotFinishDoesNotInventBoost(t *testing.T) {
	c := New()
	c.applyPrint(map[string]any{"gcode_state": "FINISH"})
	if c.PrintingOrBoost(30) {
		t.Fatal("cold start already finished: no boost, so auto can turn the switch off")
	}
	if !c.HasPrintState() {
		t.Fatal("have snapshot")
	}
}
