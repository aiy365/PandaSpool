package main

import (
	"encoding/json"
	"fmt"
	"log"
	"pandaspool/internal/store"
	"pandaspool/internal/bambu"
)

func main() {
	st, err := store.Open(".")
	if err != nil {
		log.Fatal(err)
	}

	cfg := st.LoadSettings()
	if cfg.Bambu.AccessToken == "" {
		log.Fatal("No bambu token")
	}

	adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)

	filaments, err := adapter.ListFilaments()
	if err != nil {
		log.Fatal(err)
	}

	for _, f := range filaments {
		b, _ := json.MarshalIndent(f, "", "  ")
		fmt.Printf("Filament: %s\n", string(b))
	}
}
