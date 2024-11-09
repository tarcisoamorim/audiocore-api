package main

import (
	"bytes"
	"encoding/base64"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/joho/godotenv"
)

var (
	apiKey         string
	httpClient     = &http.Client{}
	bufferPool     = sync.Pool{
		New: func() interface{} {
			return new(bytes.Buffer)
		},
	}
	allowedOrigins []string
	uploadFolder   = "/tmp/uploads"
)

// Formatos suportados como no Python
var supportedFormats = map[string]string{
	"audio/mpeg":                "mp3",
	"audio/wav":                 "wav",
	"audio/x-wav":              "wav",
	"audio/aac":                "aac",
	"audio/x-aac":              "aac",
	"audio/flac":               "flac",
	"audio/x-flac":             "flac",
	"audio/ogg":                "ogg",
	"audio/opus":               "opus",
	"audio/webm":               "webm",
	"video/webm":               "webm",
	"audio/3gpp":               "3gp",
	"audio/3gpp2":              "3g2",
	"audio/mp4":                "m4a",
	"video/mp4":                "mp4",
	"application/octet-stream": "",
}

func init() {
	devMode := flag.Bool("dev", false, "Rodar em modo de desenvolvimento")
	flag.Parse()

	if *devMode {
		if err := godotenv.Load(); err != nil {
			fmt.Println("Erro ao carregar o arquivo .env")
		}
	}

	// Criar diretório de upload
	if err := os.MkdirAll(uploadFolder, 0755); err != nil {
		fmt.Printf("Erro ao criar diretório de upload: %v\n", err)
	}

	apiKey = os.Getenv("API_KEY")
	allowOriginsEnv := os.Getenv("CORS_ALLOW_ORIGINS")
	if allowOriginsEnv != "" {
		allowedOrigins = strings.Split(allowOriginsEnv, ",")
	} else {
		allowedOrigins = []string{"*"}
	}
}

func validateAPIKey(c *gin.Context) bool {
	if apiKey == "" {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "API_KEY não configurada"})
		return false
	}

	requestApiKey := c.GetHeader("apikey")
	if requestApiKey == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "API_KEY não fornecida"})
		return false
	}

	if requestApiKey != apiKey {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "API_KEY inválida"})
		return false
	}

	return true
}

func generateTempFilename(extension string) string {
	return filepath.Join(uploadFolder, fmt.Sprintf("%s.%s", uuid.New().String(), extension))
}

// Funções de processamento de áudio adaptadas do Python
func fixAudio(inputPath, fixedInputPath string) error {
	cmd := exec.Command("ffmpeg",
		"-y",
		"-i", inputPath,
		"-vn",
		"-acodec", "libmp3lame",
		"-ar", "44100",
		"-ab", "192k",
		"-f", "mp3",
		fixedInputPath,
	)
	if output, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("erro no ffmpeg (fix_audio): %v - %s", err, string(output))
	}
	return nil
}

func convertAudio(fixedInputPath, outputPath string) error {
	cmd := exec.Command("ffmpeg",
		"-y",
		"-i", fixedInputPath,
		"-c:a", "libopus",
		"-b:a", "18.9k",
		"-ar", "16000",
		"-ac", "1",
		outputPath,
	)
	if output, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("erro no ffmpeg (convert_audio): %v - %s", err, string(output))
	}
	return nil
}

func setOpusTags(outputPath string) error {
	cmd := exec.Command("opustags",
		"--overwrite",
		"--delete-all",
		"--set-vendor", "WhatsApp",
		outputPath,
	)
	if output, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("erro no opustags: %v - %s", err, string(output))
	}
	return nil
}

func getAudioDuration(outputPath string) (int, error) {
	cmd := exec.Command("ffprobe",
		"-v", "error",
		"-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1",
		outputPath,
	)
	output, err := cmd.Output()
	if err != nil {
		return 0, fmt.Errorf("erro no ffprobe: %v", err)
	}
	duration, err := strconv.ParseFloat(strings.TrimSpace(string(output)), 64)
	if err != nil {
		return 0, err
	}
	return int(duration * 1000), nil
}

func getInputData(c *gin.Context) (string, string, error) {
	contentType := c.GetHeader("Content-Type")
	var inputPath string
	var extension string

	switch {
	case contentType == "application/octet-stream":
		data, err := io.ReadAll(c.Request.Body)
		if err != nil {
			return "", "", err
		}
		extension = "wav"
		inputPath = generateTempFilename(extension)
		if err := os.WriteFile(inputPath, data, 0644); err != nil {
			return "", "", err
		}

	case contentType == "application/json":
		var jsonData struct {
			Audio string `json:"audio"`
		}
		if err := c.BindJSON(&jsonData); err != nil {
			return "", "", err
		}
		audioData, err := base64.StdEncoding.DecodeString(jsonData.Audio)
		if err != nil {
			return "", "", err
		}
		extension = "wav"
		inputPath = generateTempFilename(extension)
		if err := os.WriteFile(inputPath, audioData, 0644); err != nil {
			return "", "", err
		}

	case strings.HasPrefix(contentType, "multipart/form-data"):
		file, err := c.FormFile("file")
		if err != nil {
			return "", "", err
		}
		
		if file.Size > 20*1024*1024 { // 20MB limit
			return "", "", errors.New("arquivo muito grande")
		}
		
		extension = supportedFormats[file.Header.Get("Content-Type")]
		if extension == "" {
			originalExt := filepath.Ext(file.Filename)
			if originalExt != "" {
				extension = strings.TrimPrefix(originalExt, ".")
			} else {
				extension = "wav"
			}
		}
		
		inputPath = generateTempFilename(extension)
		if err := c.SaveUploadedFile(file, inputPath); err != nil {
			return "", "", err
		}

	default:
		return "", "", errors.New("tipo de conteúdo não suportado")
	}

	return inputPath, extension, nil
}

func processAudio(c *gin.Context) {
	if !validateAPIKey(c) {
		return
	}

	inputPath, _, err := getInputData(c)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Criar nomes de arquivos temporários
	fixedInputPath := generateTempFilename("mp3")
	outputPath := generateTempFilename("ogg")

	defer func() {
		// Limpar arquivos temporários
		os.Remove(inputPath)
		os.Remove(fixedInputPath)
		os.Remove(outputPath)
	}()

	// Processar áudio usando a lógica do Python
	if err := fixAudio(inputPath, fixedInputPath); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := convertAudio(fixedInputPath, outputPath); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := setOpusTags(outputPath); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	duration, err := getAudioDuration(outputPath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Determinar formato de resposta
	acceptHeader := c.GetHeader("Accept")
	if strings.Contains(acceptHeader, "application/json") {
		// Retornar como JSON com base64
		audioData, err := os.ReadFile(outputPath)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "erro ao ler arquivo convertido"})
			return
		}
		base64Audio := base64.StdEncoding.EncodeToString(audioData)
		c.JSON(http.StatusOK, gin.H{
			"base64Audio": base64Audio,
			"duration_ms": duration,
		})
	} else {
		// Retornar como arquivo binário
		c.Header("Duration", fmt.Sprintf("%d", duration))
		c.FileAttachment(outputPath, "converted_audio.ogg")
	}
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	router := gin.Default()

	config := cors.DefaultConfig()
	config.AllowOrigins = allowedOrigins
	config.AllowMethods = []string{"POST", "GET", "OPTIONS"}
	config.AllowHeaders = []string{"Origin", "Content-Type", "Accept", "Authorization", "apikey"}

	router.Use(cors.New(config))
	router.POST("/convert", processAudio)

	router.Run(":" + port)
}
