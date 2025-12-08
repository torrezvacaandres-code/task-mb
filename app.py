from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import io
import zipfile
from pathlib import Path

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

def mapear_pedidos_a_plantilla(archivo_excel):
    """
    Convierte los datos del Excel de pedidos al formato de la plantilla
    """
    try:
        # Leer el archivo Excel de pedidos
        df_pedidos = pd.read_excel(archivo_excel, sheet_name='Sheet1')
        
        # Limpiar datos - eliminar filas de encabezado
        df_pedidos = df_pedidos[df_pedidos['Cliente'].notna() & 
                               (df_pedidos['Cliente'] != 'noviembre 2025 (26)') &
                               (df_pedidos['Cliente'] != '21 nov. 2025 (26)')]
        
        # Filtrar solo las filas con productos
        df_productos = df_pedidos[df_pedidos['Líneas del pedido/Producto'].notna()].copy()
        
        if df_productos.empty:
            return None, "No se encontraron productos en el archivo"
        
        # Crear DataFrame con la estructura de la plantilla
        plantilla_data = []
        
        for idx, row in df_productos.iterrows():
            # Extraer información del cliente
            cliente_info = row['Cliente']
            codigo_cliente = ""
            nombre_cliente = ""
            
            if pd.notna(cliente_info) and '[' in str(cliente_info):
                try:
                    codigo_cliente = cliente_info.split(']')[0].replace('[', '')
                    nombre_cliente = cliente_info.split('] ')[1] if '] ' in cliente_info else cliente_info
                except:
                    nombre_cliente = str(cliente_info)
            else:
                nombre_cliente = str(cliente_info) if pd.notna(cliente_info) else ""
            
            # Extraer código y descripción del producto
            producto_info = row['Líneas del pedido/Producto']
            codigo_producto = ""
            if pd.notna(producto_info) and '[' in str(producto_info):
                try:
                    codigo_producto = producto_info.split(']')[0].replace('[', '')
                except:
                    codigo_producto = str(producto_info)
            
            # Calcular valores
            cantidad = row['Líneas del pedido/Cantidad'] if pd.notna(row['Líneas del pedido/Cantidad']) else 0
            precio_unitario = row['Líneas del pedido/Precio unidad'] if pd.notna(row['Líneas del pedido/Precio unidad']) else 0
            valor_total = cantidad * precio_unitario
            
            # Fecha de pedido
            fecha_pedido = row['Fecha orden'] if pd.notna(row['Fecha orden']) else datetime.now()
            
            # Días de crédito (extraer de condiciones de pago)
            condiciones_pago = row['Condiciones de pago'] if pd.notna(row['Condiciones de pago']) else ""
            dias_credito = 0
            if 'días' in str(condiciones_pago).lower():
                try:
                    dias_credito = int(''.join(filter(str.isdigit, str(condiciones_pago))))
                except:
                    dias_credito = 15  # Default
            
            # Fecha de vencimiento
            fecha_vencimiento = fecha_pedido + timedelta(days=dias_credito) if isinstance(fecha_pedido, datetime) else ""
            
            # Crear registro para la plantilla
            registro_plantilla = {
                'Factura': f"FACT-{idx+1:04d}",  # Generar número de factura
                'Fecha de factura': fecha_pedido.strftime('%d/%m/%Y') if isinstance(fecha_pedido, datetime) else "",
                'N° PEDIDO': f"PED-{idx+1:04d}",
                'FECHA pedido': fecha_pedido.strftime('%d/%m/%Y') if isinstance(fecha_pedido, datetime) else "",
                'TIPO': "VENTA",
                'CLIENTE': codigo_cliente,
                'RAZON': nombre_cliente,
                'CIUDAD': row['Sucursal'] if pd.notna(row['Sucursal']) else "",
                'ITEM': idx + 1,
                'CODIGO': codigo_producto,
                'MARCA': "",  # No disponible en los datos originales
                'DESCRIPCION': row['Líneas del pedido/Descripción'] if pd.notna(row['Líneas del pedido/Descripción']) else "",
                'PRINCIPIO ACTIVO': "",  # No disponible en los datos originales
                'PRESENTACION': "",  # No disponible en los datos originales
                'P.LISTA FARMACIA Bs.': precio_unitario,
                'Cantidad': cantidad,
                'Valor del pedido Bs.': valor_total,
                'descuento': 0,  # No especificado en los datos originales
                'Neto de desc =Total factura': valor_total,
                'Detalle': row['Términos y condiciones'] if pd.notna(row['Términos y condiciones']) else "",
                'Mes de facturacion': fecha_pedido.strftime('%m/%Y') if isinstance(fecha_pedido, datetime) else "",
                'Dias de credito': dias_credito,
                'Fecha de vencimiento del pago': fecha_vencimiento.strftime('%d/%m/%Y') if isinstance(fecha_vencimiento, datetime) else "",
                'CxC (pago realizado)': "",
                'CxC Saldo pendiente de pago': valor_total,  # Asumiendo que no está pagado
                'Fecha de pago efectiva': "",
                'Observaciones': row['Modo de pago'] if pd.notna(row['Modo de pago']) else "",
                'fecha de vencimiento': fecha_vencimiento.strftime('%d/%m/%Y') if isinstance(fecha_vencimiento, datetime) else "",
                'LOTE': "",  # Podría extraerse de la descripción si está disponible
            }
            
            plantilla_data.append(registro_plantilla)
        
        # Crear DataFrame final
        df_plantilla = pd.DataFrame(plantilla_data)
        
        return df_plantilla, None
        
    except Exception as e:
        return None, f"Error al procesar el archivo: {str(e)}"

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
            output_filename = f'plantilla_llena_{timestamp}.csv'
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            
            # Guardar con el formato correcto (separado por punto y coma)
            df_resultado.to_csv(output_path, sep=';', index=False, encoding='utf-8')
            
            # Limpiar archivo temporal
            os.remove(filepath)
            
            flash(f'Archivo procesado exitosamente. {len(df_resultado)} registros generados.')
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