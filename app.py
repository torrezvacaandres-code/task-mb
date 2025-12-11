from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import io
import zipfile
from pathlib import Path
import re

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuración
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# Crear carpetas si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encontrar_columna(df, posibles_nombres):
    """
    Busca una columna en el DataFrame por diferentes nombres posibles (case-insensitive)
    """
    # Normalizar nombres de columnas del DataFrame
    columnas_normalizadas = {col.strip().upper(): col for col in df.columns}
    
    for nombre in posibles_nombres:
        nombre_normalizado = nombre.strip().upper()
        # Buscar coincidencia exacta
        if nombre in df.columns:
            return nombre
        # Buscar coincidencia normalizada
        if nombre_normalizado in columnas_normalizadas:
            return columnas_normalizadas[nombre_normalizado]
        # Buscar coincidencia parcial
        for col in df.columns:
            if nombre_normalizado in col.strip().upper() or col.strip().upper() in nombre_normalizado:
                return col
    return None

def extraer_lote_de_texto(texto):
    """
    Extrae el número de lote de un texto que contiene "LOTE: XXXXX"
    Si hay múltiples lotes, devuelve el primero encontrado
    """
    if not texto or pd.isna(texto):
        return ""
    
    texto_str = str(texto)
    # Buscar patrones como "LOTE: 2516172" o "LOTE:2516172"
    # Ordenados de más específico a menos específico
    patrones = [
        r'LOTE\s*:\s*(\d{7,})',  # Lotes de 7 o más dígitos (más común)
        r'LOTE\s*:\s*(\d+)',     # Cualquier número después de LOTE:
        r'LOTE\s*[:\-]\s*(\d+)', # Con guión o dos puntos
        r'LOT\s*:\s*(\d+)',      # Sin la E
        r'LOTE\s+(\d+)',         # Con espacio sin dos puntos
        r'LOTE\s*:\s*(\d{4,})',  # Al menos 4 dígitos
    ]
    
    for patron in patrones:
        matches = re.findall(patron, texto_str, re.IGNORECASE)
        if matches:
            # Devolver el primer lote encontrado (el más largo si hay varios)
            lotes_encontrados = [m for m in matches if len(m) >= 4]  # Al menos 4 dígitos
            if lotes_encontrados:
                return max(lotes_encontrados, key=len)  # Devolver el más largo
            return matches[0]
    
    return ""

def mapear_pedidos_a_plantilla(archivo_excel):
    """
    Extrae solo los campos: NIT, DESCRIPCION, Detalle, fecha de vencimiento, LOTE
    """
    try:
        # Leer el archivo Excel
        df_pedidos = pd.read_excel(archivo_excel, sheet_name=0)  # Primera hoja
        
        # Debug: mostrar las columnas encontradas
        print(f"Columnas encontradas en el archivo: {list(df_pedidos.columns)}")
        
        # Buscar columnas por diferentes nombres posibles (con búsqueda más flexible)
        col_nit = encontrar_columna(df_pedidos, ['NIT/CI:', 'NIT/CI', 'NIT', 'Nit', 'nit', 'NIT/CI/CE', 'NIT/CI/CEX', 'NIT CI'])
        col_descripcion = encontrar_columna(df_pedidos, ['DESCRIPCION', 'Descripción', 'descripcion', 'DESCRIPCIÓN', 
                                                          'Líneas del pedido/Descripción', 'Producto', 'Descripcion',
                                                          'DESCRIPCION DEL PRODUCTO'])
        col_detalle = encontrar_columna(df_pedidos, ['Detalle', 'detalle', 'DETALLE', 'Términos y condiciones', 
                                                      'Observaciones', 'Notas', 'Comentarios', 'DETALLE DEL PEDIDO'])
        col_fecha_vencimiento = encontrar_columna(df_pedidos, ['fecha de vencimiento', 'Fecha de vencimiento', 
                                                               'FECHA DE VENCIMIENTO', 'Fecha Vencimiento',
                                                               'Fecha de vencimiento del pago', 'Vencimiento',
                                                               'FECHA VENCIMIENTO'])
        col_lote = encontrar_columna(df_pedidos, ['LOTE', 'Lote', 'lote', 'LOT', 'Número de lote', 'Nro Lote',
                                                   'NUMERO DE LOTE', 'LOTE NUMERO'])
        
        # Si no encontramos NIT, intentar buscar en la primera columna o columnas numéricas
        if not col_nit and len(df_pedidos.columns) > 0:
            # Buscar en todas las columnas que puedan ser NIT
            for col in df_pedidos.columns:
                col_upper = col.upper().strip()
                # Si el nombre de la columna es muy corto o parece un código
                if len(col_upper) <= 3 or col_upper in ['NIT', 'A', 'B', 'C', 'D', 'E']:
                    # Verificar si contiene valores numéricos
                    if df_pedidos[col].dtype in ['int64', 'float64']:
                        col_nit = col
                        break
                    # O si la primera columna no es descripción ni detalle
                    elif col == df_pedidos.columns[0] and col != col_descripcion and col != col_detalle:
                        col_nit = col
                        break
        
        # Si no encontramos fecha de vencimiento directamente, intentamos calcularla
        col_fecha_pedido = encontrar_columna(df_pedidos, ['Fecha orden', 'Fecha', 'FECHA', 'Fecha pedido', 
                                                          'Fecha de pedido', 'FECHA pedido'])
        col_dias_credito = encontrar_columna(df_pedidos, ['Dias de credito', 'Días de crédito', 'Días crédito',
                                                          'Condiciones de pago', 'Dias credito'])
        
        # Debug: mostrar qué columnas se encontraron
        print(f"Columnas disponibles: {list(df_pedidos.columns)}")
        print(f"NIT encontrado en columna: {col_nit}")
        print(f"DESCRIPCION encontrada en columna: {col_descripcion}")
        print(f"Detalle encontrado en columna: {col_detalle}")
        print(f"Fecha vencimiento encontrada en columna: {col_fecha_vencimiento}")
        print(f"LOTE encontrado en columna: {col_lote}")
        
        # Crear lista para almacenar los datos
        plantilla_data = []
        
        # Procesar cada fila
        for idx, row in df_pedidos.iterrows():
            # Extraer NIT - intentar de múltiples formas
            nit = ""
            if col_nit:
                nit_val = row[col_nit]
                if pd.notna(nit_val):
                    # Convertir a string y limpiar
                    nit = str(nit_val).strip()
                    # Limpiar el NIT si tiene formato extraño
                    nit = nit.replace('nan', '').replace('NaN', '').replace('None', '')
                    # Remover puntos finales si los hay (como "NIT/CI:")
                    nit = nit.rstrip(':').strip()
                    # Si es un número, mantenerlo como string sin decimales
                    try:
                        if '.' in nit:
                            nit_float = float(nit)
                            if nit_float.is_integer():
                                nit = str(int(nit_float))
                        elif nit.replace('-', '').replace(' ', '').isdigit():
                            nit = nit  # Mantener como está si es solo dígitos
                    except:
                        pass
                # Debug para ver qué valor tiene el NIT
                if not nit:
                    print(f"Fila {idx}: NIT valor original: {nit_val}, tipo: {type(nit_val)}")
            # Si aún no hay NIT, buscar en otras columnas
            if not nit:
                # Buscar en la primera columna si no es descripción ni detalle
                if len(df_pedidos.columns) > 0:
                    primera_col = df_pedidos.columns[0]
                    if primera_col != col_descripcion and primera_col != col_detalle and primera_col != col_nit:
                        primer_val = row[primera_col]
                        if pd.notna(primer_val):
                            primer_str = str(primer_val).strip()
                            # Si parece un número o código, usarlo como NIT
                            if primer_str.replace('.', '').replace('-', '').replace(' ', '').isdigit():
                                nit = primer_str
                # Si aún no hay NIT, buscar en todas las columnas numéricas
                if not nit:
                    for col in df_pedidos.columns:
                        if col not in [col_descripcion, col_detalle, col_fecha_vencimiento, col_lote]:
                            val = row[col]
                            if pd.notna(val):
                                val_str = str(val).strip()
                                # Si es un número entero corto (posible NIT)
                                if val_str.replace('.', '').replace('-', '').isdigit() and len(val_str.replace('.', '').replace('-', '')) <= 15:
                                    nit = val_str.replace('.0', '').replace('.', '')
                                    break
            
            # Extraer DESCRIPCION
            descripcion = ""
            if col_descripcion:
                desc_val = row[col_descripcion]
                if pd.notna(desc_val):
                    descripcion = str(desc_val).strip()
            
            # Extraer Detalle
            detalle = ""
            if col_detalle:
                det_val = row[col_detalle]
                if pd.notna(det_val):
                    detalle = str(det_val).strip()
            
            # Extraer o calcular fecha de vencimiento
            fecha_vencimiento = ""
            if col_fecha_vencimiento:
                fecha_val = row[col_fecha_vencimiento]
                if pd.notna(fecha_val):
                    if isinstance(fecha_val, datetime):
                        fecha_vencimiento = fecha_val.strftime('%d/%m/%Y')
                    elif isinstance(fecha_val, pd.Timestamp):
                        fecha_vencimiento = fecha_val.strftime('%d/%m/%Y')
                    else:
                        fecha_str = str(fecha_val).strip()
                        # Intentar parsear si es una fecha en texto
                        try:
                            fecha_parsed = pd.to_datetime(fecha_str, dayfirst=True)
                            fecha_vencimiento = fecha_parsed.strftime('%d/%m/%Y')
                        except:
                            fecha_vencimiento = fecha_str
            # Si no hay fecha de vencimiento directa, calcularla
            if not fecha_vencimiento:
                if col_fecha_pedido and col_dias_credito:
                    # Calcular fecha de vencimiento desde fecha pedido y días crédito
                    fecha_pedido = row[col_fecha_pedido]
                    dias_credito = 0
                    
                    if pd.notna(fecha_pedido):
                        if not isinstance(fecha_pedido, datetime):
                            try:
                                fecha_pedido = pd.to_datetime(fecha_pedido)
                            except:
                                fecha_pedido = None
                        
                        if fecha_pedido and pd.notna(row[col_dias_credito]):
                            cond_pago = str(row[col_dias_credito])
                            # Buscar días en el texto (ej: "15 días", "30 Días")
                            if 'días' in cond_pago.lower() or 'dias' in cond_pago.lower():
                                try:
                                    dias_credito = int(''.join(filter(str.isdigit, cond_pago)))
                                except:
                                    dias_credito = 0
                            else:
                                try:
                                    dias_credito = int(row[col_dias_credito])
                                except:
                                    dias_credito = 0
                        
                        if fecha_pedido and dias_credito > 0:
                            fecha_vencimiento = (fecha_pedido + timedelta(days=dias_credito)).strftime('%d/%m/%Y')
                        elif fecha_pedido:
                            # Si hay fecha pero no días, usar fecha pedido como vencimiento
                            fecha_vencimiento = fecha_pedido.strftime('%d/%m/%Y')
            
            # Extraer LOTE - SIEMPRE intentar extraerlo de la descripción primero
            lote = ""
            # Primero intentar extraer de la descripción (más confiable)
            if descripcion:
                lote = extraer_lote_de_texto(descripcion)
                # Debug para ver si se encontró el lote
                if not lote and idx < 3:  # Solo para las primeras 3 filas
                    print(f"Fila {idx}: No se encontró LOTE en descripción: {descripcion[:100]}")
            
            # Si no se encontró en la descripción, intentar de columna dedicada
            if not lote and col_lote:
                lote_val = row[col_lote]
                if pd.notna(lote_val):
                    lote_temp = str(lote_val).strip()
                    lote_temp = lote_temp.replace('nan', '').replace('NaN', '').replace('None', '')
                    if lote_temp and lote_temp.isdigit():
                        lote = lote_temp
            
            # Crear registro solo con los campos solicitados
            registro = {
                'NIT': nit,
                'DESCRIPCION': descripcion,
                'Detalle': detalle,
                'fecha de vencimiento': fecha_vencimiento,
                'LOTE': lote
            }
            
            plantilla_data.append(registro)
        
        # Crear DataFrame final solo con los campos solicitados
        df_plantilla = pd.DataFrame(plantilla_data)
        
        # Eliminar filas completamente vacías
        df_plantilla = df_plantilla.dropna(how='all')
        
        # Eliminar filas donde todos los campos están vacíos o son solo espacios
        df_plantilla = df_plantilla[df_plantilla.astype(str).apply(lambda x: x.str.strip()).ne('').any(axis=1)]
        
        if df_plantilla.empty:
            return None, "No se encontraron datos en el archivo"
        
        return df_plantilla, None
        
    except Exception as e:
        import traceback
        error_detalle = f"Error al procesar el archivo: {str(e)}\n{traceback.format_exc()}"
        return None, error_detalle

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Procesar el archivo
            df_resultado, error = mapear_pedidos_a_plantilla(filepath)
            
            if error:
                flash(f'Error al procesar: {error}')
                return redirect(url_for('index'))
            
            # Guardar el resultado
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f'campos_extraidos_{timestamp}.csv'
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            
            # Guardar con el formato correcto (separado por punto y coma)
            df_resultado.to_csv(output_path, sep=';', index=False, encoding='utf-8')
            
            # Limpiar archivo temporal
            os.remove(filepath)
            
            flash(f'Archivo procesado exitosamente. {len(df_resultado)} registros con los campos: NIT, DESCRIPCION, Detalle, fecha de vencimiento y LOTE.')
            return send_file(output_path, as_attachment=True, download_name=output_filename)
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}')
            return redirect(url_for('index'))
    else:
        flash('Tipo de archivo no permitido. Use archivos Excel (.xlsx, .xls)')
        return redirect(url_for('index'))

@app.route('/preview')
def preview():
    # Mostrar una vista previa de cómo funciona el mapeo
    return render_template('preview.html')

@app.route('/health')
def health_check():
    """Health check endpoint for container monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'pedidos-processor'
    }), 200

@app.errorhandler(413)
def too_large(e):
    flash('El archivo es demasiado grande. Máximo 16MB.')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(e):
    flash('Error interno del servidor. Por favor, intenta nuevamente.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)