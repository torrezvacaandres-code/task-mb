import pandas as pd
import os
from pathlib import Path

def analizar_excel_pedidos():
    """
    Lee y analiza el archivo Excel de pedidos de ventas
    """
    # Ruta del archivo Excel
    archivo_excel = r"c:\Users\atorrez\Desktop\mb\examples\Pedidos de Venta (sale.order) (35).xlsx"
    
    print(f"Analizando archivo: {archivo_excel}")
    print("=" * 80)
    
    try:
        # Verificar que el archivo existe
        if not os.path.exists(archivo_excel):
            print(f"ERROR: El archivo no existe en la ruta: {archivo_excel}")
            return
        
        # Leer información básica del archivo Excel
        xl_file = pd.ExcelFile(archivo_excel)
        print(f"Hojas disponibles en el Excel: {xl_file.sheet_names}")
        print(f"Número total de hojas: {len(xl_file.sheet_names)}")
        print()
        
        # Analizar cada hoja del Excel
        for i, sheet_name in enumerate(xl_file.sheet_names):
            print(f"--- HOJA {i+1}: '{sheet_name}' ---")
            
            # Leer la hoja
            df = pd.read_excel(archivo_excel, sheet_name=sheet_name)
            
            # Información básica de la hoja
            print(f"Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
            
            if not df.empty:
                print(f"Columnas disponibles:")
                for j, col in enumerate(df.columns):
                    print(f"  {j+1}. {col}")
                
                print(f"\nPrimeras 3 filas de datos:")
                print(df.head(3).to_string(max_cols=None, max_colwidth=50))
                
                print(f"\nTipos de datos:")
                print(df.dtypes.to_string())
                
                # Buscar columnas que podrían ser relevantes para pedidos de ventas
                columnas_importantes = []
                palabras_clave = ['pedido', 'venta', 'cliente', 'producto', 'cantidad', 'precio', 'total', 'fecha', 'estado']
                
                for col in df.columns:
                    col_lower = str(col).lower()
                    for palabra in palabras_clave:
                        if palabra in col_lower:
                            columnas_importantes.append(col)
                            break
                
                if columnas_importantes:
                    print(f"\nColumnas potencialmente importantes para pedidos de ventas:")
                    for col in columnas_importantes:
                        print(f"  - {col}")
                
                # Mostrar estadísticas básicas para columnas numéricas
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    print(f"\nEstadísticas de columnas numéricas:")
                    print(df[numeric_cols].describe().to_string())
                
                # Verificar valores nulos
                valores_nulos = df.isnull().sum()
                if valores_nulos.sum() > 0:
                    print(f"\nValores nulos por columna:")
                    for col, nulos in valores_nulos.items():
                        if nulos > 0:
                            print(f"  {col}: {nulos} valores nulos")
            else:
                print("La hoja está vacía")
            
            print("\n" + "="*80 + "\n")
    
    except Exception as e:
        print(f"Error al procesar el archivo: {str(e)}")
        print(f"Tipo de error: {type(e).__name__}")

if __name__ == "__main__":
    analizar_excel_pedidos()