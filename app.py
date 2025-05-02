from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
import easyocr
import pandas as pd
import re
import os
import tempfile

app = FastAPI()
reader = easyocr.Reader(['es'], gpu=False)

palabras_producto = [
    "cristal", "escudo", "heineken", "budweiser", "corona", "becker", "royal guard",
    "stella", "baltica", "kuntsmann", "cusqueña", "quilmes", "lager", "schop",
    "coca", "coca cola", "fanta", "sprite", "bilz", "pap", "kem", "crush", "pepsi",
    "red bull", "monster", "score", "volt",
    "vital", "benedictino", "andina del valle", "aquarius", "watts", "jugo",
    "gato", "santa helena", "misiones", "reservado", "tarapaca", "carmenere", "carolina",
    "alto del carmen", "capel", "mistral", "control", "ron", "barcelo", "bacardi",
    "whisky", "jb", "jack daniels", "absolut", "vodka", "fernet", "jagermeister",
    "pack", "lata", "botella", "retornable", "desechable", "x", "six pack"
]

def limpiar_numero(n: str) -> float:
    return float(n.replace(".", "").replace(",", "."))

def extraer_productos(lineas):
    productos = []
    i = 0
    while i <= len(lineas) - 5:
        l1, l2, l3, l4, l5 = lineas[i:i+5]
        if any(p in l1.lower() for p in palabras_producto) and \
           re.match(r"^\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{1,2})?$", l2) and \
           re.match(r"^\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{1,2})?$", l3) and \
           re.search(r"lata|botella|pack|x|retornable|desechable", l4.lower()) and \
           re.match(r"^\d+[\.,]?\d*$", l5):

            try:
                productos.append({
                    "Producto": l1.strip(),
                    "Cantidad": limpiar_numero(l5),
                    "Precio Unitario": limpiar_numero(l3),
                    "Precio Total": limpiar_numero(l2)
                })
                i += 5
            except ValueError:
                i += 1
        else:
            i += 1
    return productos

@app.post("/procesar_factura")
async def procesar_factura(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=400, detail="Formato no soportado. Usa JPG, JPEG o PNG.")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        resultados = reader.readtext(tmp_path)
        lineas = [res[1].strip() for res in resultados if res[1].strip()]
        productos = extraer_productos(lineas)

        if not productos:
            return JSONResponse({"mensaje": "No se detectaron productos."}, status_code=200)

        df = pd.DataFrame(productos)
        nombre_excel = tmp_path.replace(".jpg", ".xlsx")
        df.to_excel(nombre_excel, index=False)

        return FileResponse(nombre_excel, filename="productos_detectados.xlsx")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la factura: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
