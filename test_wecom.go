package main

import (
	"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"encoding/binary"
	"fmt"
)

func verify(echostr, encodingAESKey string) string {
	aesKey, _ := base64.StdEncoding.DecodeString(encodingAESKey + "=")
	ciphertext, _ := base64.StdEncoding.DecodeString(echostr)

	block, err := aes.NewCipher(aesKey)
	if err != nil {
		return ""
	}
	mode := cipher.NewCBCDecrypter(block, aesKey[:16])

	plaintext := make([]byte, len(ciphertext))
	mode.CryptBlocks(plaintext, ciphertext)

	pad := int(plaintext[len(plaintext)-1])
	if len(plaintext) < pad {
		return ""
	}
	plaintext = plaintext[:len(plaintext)-pad]

	if len(plaintext) < 20 {
		return ""
	}
	content := plaintext[16:]

	msgLen := binary.BigEndian.Uint32(content[:4])
	if len(content) < int(4+msgLen) {
		return ""
	}

	msg := content[4 : 4+msgLen]
	return string(msg)
}

func main() {
	fmt.Println("works")
}
