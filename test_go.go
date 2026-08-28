
package main

import (
	"fmt"
	"log"
	"printpilot-hub/internal/store"
)

func main() {
	st, err := store.Open("data")
	if err != nil {
		log.Fatal(err)
	}
	prods, err := st.ListProducts()
	fmt.Println("Products returned:", len(prods))
	if err != nil {
		fmt.Println("ERROR:", err)
	}
}

