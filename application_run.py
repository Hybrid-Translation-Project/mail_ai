import uvicorn

if __name__ == "__main__":
    # Bu dosya ana dizinde olduğu için "app" klasörünü direkt görür.
    # reload=True: Kodda değişiklik yaparsan sunucuyu otomatik yeniden başlatır (geliştirici modu).
    print("🚀 Sistem Code Runner ile Ana Dizinden Başlatılıyor...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)   