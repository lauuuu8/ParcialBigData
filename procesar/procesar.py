import boto3
import os
import csv
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse
import json
import io

# Inicializar cliente S3
s3 = boto3.client('s3')

def app(event, context):
    print("==== Evento recibido por Lambda ====")
    print(json.dumps(event, indent=2))
    
    # Obtener configuraciones de variables de entorno
    BUCKET_NAME = os.environ.get('BUCKET_NAME', 'eltiempop')  # Valor por defecto 'parci4l3'
    BASE_URLS = {
        'publimetro': os.environ.get('PUBLIMETRO_URL', 'https://www.publimetro.co'),
        'eltiempo': os.environ.get('ELTIEMPO_URL', 'https://www.eltiempo.com')
    }
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

    # Verificar si el evento tiene la estructura esperada
    if 'Records' not in event:
        error_msg = "Evento no contiene 'Records'. Formato inesperado."
        print(error_msg)
        return {
            "statusCode": 400,
            "body": json.dumps({"error": error_msg})
        }

    for record in event['Records']:
        try:
            bucket = record['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(record['s3']['object']['key'])

            if not key.startswith('headlines/raw/') or not key.endswith('.html'):
                print(f"Ignorando archivo no válido para procesamiento: {key}")
                continue

            print(f"Procesando archivo S3: bucket={bucket}, key={key}")

            # Obtener el contenido del archivo HTML
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            print(f"Archivo HTML extraído correctamente: {key}")

            # Parsear el HTML
            soup = BeautifulSoup(content, 'html.parser')
            nombre_archivo = os.path.basename(key)

            # Detectar el periódico por el nombre del archivo
            if 'publimetro' in nombre_archivo:
                periodico = 'publimetro'
            elif 'eltiempo' in nombre_archivo:
                periodico = 'eltiempo'
            else:
                periodico = 'desconocido'
                print(f"Periódico no reconocido en el archivo: {nombre_archivo}")

            noticias = []

            # Extraer noticias de etiquetas <article>
            for article in soup.find_all('article'):
                titular_tag = article.find(['h1', 'h2', 'h3'])
                enlace_tag = article.find('a', href=True)

                if titular_tag and enlace_tag:
                    titular = titular_tag.get_text(strip=True)
                    enlace = enlace_tag['href']
                    
                    if not enlace.startswith('http'):
                        enlace = f"{BASE_URLS.get(periodico, '')}{enlace}"

                    categoria = ''
                    parts = enlace.split('/')
                    if len(parts) > 3:
                        categoria = parts[3]

                    noticias.append({
                        'categoria': categoria,
                        'titular': titular,
                        'enlace': enlace
                    })

            # Fallback si no se encontraron noticias en <article>
            if not noticias:
                print("No se encontraron artículos válidos en <article>. Se intenta fallback...")
                for heading in soup.find_all(['h1', 'h2', 'h3']):
                    a_tag = heading.find('a', href=True)
                    if a_tag:
                        titular = heading.get_text(strip=True)
                        enlace = a_tag['href']
                        
                        if not enlace.startswith('http'):
                            enlace = f"{BASE_URLS.get(periodico, '')}{enlace}"

                        categoria = ''
                        parts = enlace.split('/')
                        if len(parts) > 3:
                            categoria = parts[3]

                        noticias.append({
                            'categoria': categoria,
                            'titular': titular,
                            'enlace': enlace
                        })

            print(f"Total de noticias extraídas: {len(noticias)} del periódico {periodico}")

            # Generar estructura de carpetas por fecha
            fecha = datetime.utcnow()
            year = fecha.strftime('%Y')
            month = fecha.strftime('%m')
            day = fecha.strftime('%d')
            hour = fecha.strftime('%H')
            minute = fecha.strftime('%M')

            # Ruta para el archivo CSV
            csv_key = f"headlines/final/periodico={periodico}/year={year}/month={month}/day={day}/noticias_{hour}-{minute}.csv"
            print(f"Guardando CSV en: {csv_key}")

            # Crear CSV en memoria
            csv_buffer = io.StringIO()
            writer = csv.DictWriter(csv_buffer, fieldnames=['categoria', 'titular', 'enlace'])
            writer.writeheader()
            for noticia in noticias:
                writer.writerow(noticia)

            # Subir CSV a S3
            s3.put_object(
                Bucket=bucket,
                Key=csv_key,
                Body=csv_buffer.getvalue(),
                ContentType='text/csv'
            )
            print("Archivo CSV subido exitosamente a S3.")

        except Exception as e:
            print(f"Error procesando el archivo {key}: {str(e)}")
            continue

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Procesamiento completado",
            "noticias_procesadas": sum(1 for record in event['Records'] if 's3' in record)
        })
    }