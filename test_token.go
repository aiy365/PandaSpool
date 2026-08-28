package main

import (
	"fmt"
	"log"
	"pandaspool/internal/store"
)

func main() {
	st, err := store.Open(".")
	if err != nil {
		log.Fatal(err)
	}

	cfg := st.LoadSettings()
	fmt.Printf("Token: '%s'\n", cfg.Bambu.AccessToken)
}
