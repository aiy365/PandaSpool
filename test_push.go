
package main

import (
	"fmt"
	"time"
	"printpilot-hub/internal/bambu"
)

func main() {
	client := bambu.New()
	client.Configure("cn", "15521066126", "Yao365365!", "03900D642006297", "AQB9moijNyTk9F6TfFd_-WRSe6Jiug7Dk-FhVusQsBKXAkHbzAaOliR5milE9EiAPZ626WKUoKWqnMzysDGUabmToBMshFjGU0I9qFTy1V5V-KtzSLvQzLaWrhx28R1_Nht-Glvk_cUws6al")
	client.Reconnect()
	
	fmt.Println("Waiting for connection...")
	time.Sleep(3 * time.Second)
	
	fmt.Println("Pushing ami_assign_info for External Spool...")
	err := client.SetFilament(255, 254, "GFG00", "00FF00FF", "PETG") 
	if err != nil {
		fmt.Println("Error:", err)
	} else {
		fmt.Println("Push complete.")
	}
	
	fmt.Println("Pushing ami_assign_info for AMS Slot 1...")
	err2 := client.SetFilament(0, 0, "GFG00", "0000FFFF", "PETG")
	if err2 != nil {
		fmt.Println("Error2:", err2)
	}
	time.Sleep(2 * time.Second)
	fmt.Println("Done")
}

