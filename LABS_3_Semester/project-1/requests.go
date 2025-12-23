package main

import (
	"bytes"
	"fmt"
	"io/ioutil"
	"net"
	"net/http"
	"time"
)

func startServer(addr chan string) {
	mux := http.NewServeMux()

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "getHandler: incoming request\n")
		fmt.Fprintf(w, "getHandler: r.Url %#v\n", r.URL)
	})

	mux.HandleFunc("/raw_body", func(w http.ResponseWriter, r *http.Request) {
		body, err := ioutil.ReadAll(r.Body)
		defer r.Body.Close()
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		fmt.Fprintf(w, "postHandler: raw body %s\n", string(body))
	})

	server := &http.Server{Handler: mux}
	listener, _ := net.Listen("tcp", ":0")
	addr <- listener.Addr().String()

	server.Serve(listener)
}

func runGet(serverURL string) {
	url := serverURL + "/?param=123&param2=test"
	resp, err := http.Get(url)
	if err != nil {
		fmt.Println("error happend", err)
		return
	}
	defer resp.Body.Close()

	respBody, err := ioutil.ReadAll(resp.Body)
	fmt.Printf("http.Get body %#v\n\n\n", string(respBody))
}

func runGetFullReq(serverURL string) {
	fullURL := serverURL + "/?id=42&user=rvasily"

	req, _ := http.NewRequest(http.MethodGet, fullURL, nil)
	req.Header.Set("User-Agent", "coursera/golang")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		fmt.Println("error happend", err)
		return
	}
	defer resp.Body.Close()

	respBody, err := ioutil.ReadAll(resp.Body)
	fmt.Printf("testGetFullReq resp %#v\n\n\n", string(respBody))
}

func runTransportAndPost(serverURL string) {
	transport := &http.Transport{
		DialContext: (&net.Dialer{
			Timeout:   30 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		MaxIdleConns: 100,
	}

	client := &http.Client{
		Timeout:   time.Second * 10,
		Transport: transport,
	}

	data := `{"id": 42, "user": "rvasily"}`
	body := bytes.NewBufferString(data)

	url := serverURL + "/raw_body"
	req, _ := http.NewRequest(http.MethodPost, url, body)
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("error happend", err)
		return
	}
	defer resp.Body.Close()

	respBody, err := ioutil.ReadAll(resp.Body)
	fmt.Printf("runTransport %#v\n\n\n", string(respBody))
}

func main() {
	addr := make(chan string)
	go startServer(addr)

	serverURL := "http://" + <-addr
	fmt.Println("Server started at:", serverURL)

	runGet(serverURL)
	runGetFullReq(serverURL)
	runTransportAndPost(serverURL)
}
