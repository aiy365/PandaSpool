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
	
	spools, err := st.ListSpools()
	if err != nil {
		log.Fatal(err)
	}

	cfg := st.LoadSettings()
	if cfg.Bambu.AccessToken == "" {
		log.Fatal("No bambu token")
	}

	adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)

	var ids []int64
	for _, sp := range spools {
		if sp.BambuCloudID > 0 {
			ids = append(ids, sp.BambuCloudID)
		}
	}

	fmt.Printf("Deleting %d filaments from Bambu Cloud...\n", len(ids))
	
	chunkSize := 50
	for i := 0; i < len(ids); i += chunkSize {
		end := i + chunkSize
		if end > len(ids) {
			end = len(ids)
		}
		chunk := ids[i:end]
		err := adapter.DeleteFilaments(chunk)
		if err != nil {
			fmt.Printf("Error deleting chunk: %v\n", err)
		} else {
			fmt.Printf("Deleted chunk: %v\n", chunk)
		}
	}

	fmt.Println("Done deleting from Bambu Cloud.")
}
