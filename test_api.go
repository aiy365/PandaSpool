
package main
import (
	"fmt"
	"io/ioutil"
	"net/http"
)
func main() {
	url := "https://api.bambulab.cn/v1/design-user-service/my/filament"
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("Authorization", "Bearer AQB9moijNyTk9F6TfFd_-WRSe6Jiug7Dk-FhVusQsBKXAkHbzAaOliR5milE9EiAPZ626WKUoKWqnMzysDGUabmToBMshFjGU0I9qFTy1V5V-KtzSLvQzLaWrhx28R1_Nht-Glvk_cUws6al")
	
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("Error:", err)
		return
	}
	defer resp.Body.Close()
	body, _ := ioutil.ReadAll(resp.Body)
	fmt.Println("Status:", resp.Status)
	fmt.Println("Body:", string(body))
}

