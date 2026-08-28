package main

import (
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

	fmt.Printf("Total Spools Found: %d\n", len(filaments))
	for _, f := range filaments {
		fmt.Printf("Vendor: %s | Name: %s | ID: %s | Category: %s\n", f.FilamentVendor, f.FilamentName, f.FilamentID, f.Category)
	}
}
