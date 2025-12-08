import pandas as pd
import numpy as np
from datetime import datetime

def procesar_pedidos_ventas():
    """
    Procesa y limpia los datos del Excel de pedidos de ventas
    """
    archivo_excel = r"c:\Users\atorrez\Desktop\mb\examples\Pedidos de Venta (sale.order) (35).xlsx"
    
    print("ANÁLISIS DETALLADO DE PEDIDOS DE VENTAS")
    print("=" * 50)
    
    # Leer el archivo Excel
    df = pd.read_excel(archivo_excel, sheet_name='Sheet1')
    
    print(f"Datos originales: {df.shape[0]} filas, {df.shape[1]} columnas")
    
    # Limpiar datos - eliminar filas completamente vacías o de encabezado
    df_limpio = df.copy()
    
    # Eliminar las primeras filas que parecen ser encabezados
    df_limpio = df_limpio[df_limpio['Cliente'].notna() & 
                         (df_limpio['Cliente'] != 'noviembre 2025 (26)') &
                         (df_limpio['Cliente'] != '21 nov. 2025 (26)')]
    
    print(f"Datos después de limpieza básica: {df_limpio.shape[0]} filas")
    
    # Análisis de clientes únicos
    clientes_unicos = df_limpio['Cliente'].dropna().unique()
    print(f"\nClientes únicos en el archivo: {len(clientes_unicos)}")
    for i, cliente in enumerate(clientes_unicos, 1):
        print(f"  {i}. {cliente}")
    
    # Análisis de productos
    productos = df_limpio['Líneas del pedido/Producto'].dropna()
    productos_unicos = productos.unique()
    print(f"\nProductos únicos: {len(productos_unicos)}")
    print("Primeros 10 productos:")
    for i, producto in enumerate(productos_unicos[:10], 1):
        print(f"  {i}. {producto}")
    
    # Análisis de ventas por cliente
    print(f"\nANÁLISIS POR CLIENTE:")
    print("-" * 30)
    
    for cliente in clientes_unicos:
        pedidos_cliente = df_limpio[df_limpio['Cliente'] == cliente]
        
        # Filtrar solo las líneas con productos (no NaN)
        lineas_productos = pedidos_cliente[pedidos_cliente['Líneas del pedido/Producto'].notna()]
        
        if len(lineas_productos) > 0:
            total_cantidad = lineas_productos['Líneas del pedido/Cantidad'].sum()
            total_valor = (lineas_productos['Líneas del pedido/Cantidad'] * 
                          lineas_productos['Líneas del pedido/Precio unidad']).sum()
            
            print(f"\n{cliente}:")
            print(f"  - Líneas de producto: {len(lineas_productos)}")
            print(f"  - Cantidad total: {total_cantidad:.0f} unidades")
            print(f"  - Valor total: ${total_valor:,.2f}")
            
            # Fechas del cliente
            fechas_cliente = pedidos_cliente['Fecha orden'].dropna()
            if len(fechas_cliente) > 0:
                fecha_primera = fechas_cliente.min()
                fecha_ultima = fechas_cliente.max()
                print(f"  - Primera orden: {fecha_primera}")
                if fecha_primera != fecha_ultima:
                    print(f"  - Última orden: {fecha_ultima}")
    
    # Resumen general
    print(f"\nRESUMEN GENERAL:")
    print("-" * 20)
    
    # Solo considerar filas con datos de productos
    datos_productos = df_limpio[df_limpio['Líneas del pedido/Producto'].notna()]
    
    if len(datos_productos) > 0:
        total_lineas = len(datos_productos)
        cantidad_total = datos_productos['Líneas del pedido/Cantidad'].sum()
        valor_total = (datos_productos['Líneas del pedido/Cantidad'] * 
                      datos_productos['Líneas del pedido/Precio unidad']).sum()
        
        print(f"Total de líneas de productos: {total_lineas}")
        print(f"Cantidad total vendida: {cantidad_total:.0f} unidades")
        print(f"Valor total de ventas: ${valor_total:,.2f}")
        print(f"Precio promedio por unidad: ${datos_productos['Líneas del pedido/Precio unidad'].mean():.2f}")
        print(f"Cantidad promedio por línea: {datos_productos['Líneas del pedido/Cantidad'].mean():.1f}")
    
    # Guardar datos limpios en un nuevo archivo CSV
    archivo_limpio = "pedidos_ventas_procesados.csv"
    datos_productos.to_csv(archivo_limpio, index=False, encoding='utf-8')
    print(f"\nDatos procesados guardados en: {archivo_limpio}")
    
    return datos_productos

if __name__ == "__main__":
    df_procesado = procesar_pedidos_ventas()