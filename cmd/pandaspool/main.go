package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"pandaspool/internal/server"
)

func main() {
	dataDir := env("PRINTPILOT_DATA_DIR", "./data")
	listen := env("PRINTPILOT_LISTEN", "127.0.0.1:8088")
	srv, err := server.New(dataDir, listen)
	if err != nil {
		log.Fatal(err)
	}
	go func() {
		log.Printf("pandaspool listening on http://%s  data=%s", listen, dataDir)
		if err := srv.ListenAndServe(); err != nil {
			log.Fatal(err)
		}
	}()
	ch := make(chan os.Signal, 1)
	signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
	<-ch
	_ = srv.Close()
}

func env(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}
