"""
Andreu Snijders Trullàs
Adrián Fernández Beserán

Este módulo proporciona funciones para manejar canales de audio estéreo en archivos WAVE,
incluyendo la conversión a mono y la codificación/decodificación para compatibilidad con mono.
"""

import struct

def leer_cabecera_wav(archivo):
    """
    Lee la cabecera de un archivo WAVE y verifica que sea válida.
    
    Parámetros:
    archivo (str): Nombre del archivo WAVE de entrada.
    
    Retorna:
    dict: Un diccionario con los parámetros del archivo WAVE.
    """
    with open(archivo, 'rb') as f:
        # Lee los primeros 44 bytes que corresponden a la cabecera del archivo WAVE
        cabecera = f.read(44)
        if len(cabecera) != 44:
            raise ValueError("El archivo WAVE no tiene una cabecera válida de 44 bytes.")
        
        # Desempaqueta la cabecera WAVE
        riff, tamaño, wave, fmt, longitud_fmt, formato, canales, frecuencia, bps, block_align, bits_per_sample, data, data_tamaño = struct.unpack('<4sI4s4sIHHIIHH4sI', cabecera)
        
        # Verifica la validez de la cabecera comprobando los valores esperados
        if riff != b'RIFF' or wave != b'WAVE' or fmt != b'fmt ' or data != b'data':
            raise ValueError("El archivo WAVE no tiene una cabecera válida.")
        
        # Retorna un diccionario con los parámetros del archivo WAVE
        return {
            'canales': canales,
            'frecuencia': frecuencia,
            'bits_per_sample': bits_per_sample,
            'data_tamaño': data_tamaño,
            'cabecera': cabecera
        }

def escribir_cabecera_wav(archivo, params, data_tamaño):
    """
    Escribe una cabecera WAVE en un archivo.
    
    Parámetros:
    archivo (str): Nombre del archivo WAVE de salida.
    params (dict): Diccionario con los parámetros del archivo WAVE.
    data_tamaño (int): Tamaño de los datos de audio.
    """
    # Calcula el tamaño total del chunk RIFF
    riff_tamaño = 36 + data_tamaño
    
    with open(archivo, 'wb') as f:
        # Empaqueta la cabecera WAVE con los parámetros proporcionados
        cabecera = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF', riff_tamaño, b'WAVE', b'fmt ', 16,
            1, params['canales'], params['frecuencia'], 
            params['frecuencia'] * params['canales'] * params['bits_per_sample'] // 8,
            params['canales'] * params['bits_per_sample'] // 8, 
            params['bits_per_sample'], b'data', data_tamaño
        )
        # Escribe la cabecera en el archivo
        f.write(cabecera)

def estereo2mono(ficEste, ficMono, canal=2):
    """
    Convierte un archivo WAVE estéreo a mono.
    
    Parámetros:
    ficEste (str): Nombre del archivo WAVE estéreo de entrada.
    ficMono (str): Nombre del archivo WAVE mono de salida.
    canal (int): Canal a extraer: 0=izquierdo, 1=derecho, 2=semisuma, 3=semidiferencia.
    """
    params = leer_cabecera_wav(ficEste)
    if params['canales'] != 2 or params['bits_per_sample'] != 16:
        raise ValueError("El archivo de entrada debe ser un archivo WAVE estéreo con muestras de 16 bits.")
    
    with open(ficEste, 'rb') as infile:
        infile.seek(44)  # Salta la cabecera
        frames = infile.read(params['data_tamaño'])  # Lee los datos de audio
        
        # Determina la operación a realizar según el canal especificado
        operaciones = {
            0: lambda l, r: l,
            1: lambda l, r: r,
            2: lambda l, r: (l + r) // 2,
            3: lambda l, r: (l - r) // 2
        }
        operacion = operaciones[canal]

        # Calcula las muestras mono de acuerdo al canal especificado
        out_frames = bytearray(
            struct.pack('<h', operacion(left, right))
            for left, right in (struct.unpack('<hh', frames[i:i+4]) for i in range(0, len(frames), 4))
        )

    escribir_cabecera_wav(ficMono, {'canales': 1, 'frecuencia': params['frecuencia'], 'bits_per_sample': 16}, len(out_frames))
    
    with open(ficMono, 'ab') as outfile:
        outfile.write(out_frames)

def mono2estereo(ficIzq, ficDer, ficEste):
    """
    Combina dos archivos WAVE mono en un archivo WAVE estéreo.
    
    Parámetros:
    ficIzq (str): Nombre del archivo WAVE mono del canal izquierdo.
    ficDer (str): Nombre del archivo WAVE mono del canal derecho.
    ficEste (str): Nombre del archivo WAVE estéreo de salida.
    """
    params_izq = leer_cabecera_wav(ficIzq)
    params_der = leer_cabecera_wav(ficDer)

    if params_izq['canales'] != 1 or params_izq['bits_per_sample'] != 16 or params_der['canales'] != 1 or params_der['bits_per_sample'] != 16 or params_izq['frecuencia'] != params_der['frecuencia'] or params_izq['data_tamaño'] != params_der['data_tamaño']:
        raise ValueError("Los archivos de entrada deben ser archivos WAVE mono con los mismos parámetros.")
    
    with open(ficIzq, 'rb') as leftfile, open(ficDer, 'rb') as rightfile:
        leftfile.seek(44)  # Salta la cabecera
        rightfile.seek(44)  # Salta la cabecera
        frames_left = leftfile.read(params_izq['data_tamaño'])
        frames_right = rightfile.read(params_der['data_tamaño'])

        # Combina las muestras de los canales izquierdo y derecho en estéreo
        out_frames = bytearray(
            frame_izq + frame_der
            for frame_izq, frame_der in zip(
                (frames_left[i:i+2] for i in range(0, len(frames_left), 2)),
                (frames_right[i:i+2] for i in range(0, len(frames_right), 2))
            )
        )

    escribir_cabecera_wav(ficEste, {'canales': 2, 'frecuencia': params_izq['frecuencia'], 'bits_per_sample': 16}, len(out_frames))
    
    with open(ficEste, 'ab') as outfile:
        outfile.write(out_frames)
        
def codEstereo(ficEste, ficCod):
    """
    Codifica un archivo WAVE estéreo en una señal de 32 bits compatible con mono.
    
    Parámetros:
    ficEste (str): Nombre del archivo WAVE estéreo de entrada.
    ficCod (str): Nombre del archivo WAVE codificado de salida.
    """
    params = leer_cabecera_wav(ficEste)
    if params['canales'] != 2 or params['bits_per_sample'] != 16:
        raise ValueError("El archivo de entrada debe ser un archivo WAVE estéreo con muestras de 16 bits.")
    
    with open(ficEste, 'rb') as infile:
        infile.seek(44)  # Salta la cabecera
        frames = infile.read(params['data_tamaño'])  # Lee los datos de audio

        # Codifica las muestras estéreo en una señal de 32 bits
        out_frames = bytearray(
            struct.pack('<i', ((left + right) // 2 << 16) | ((left - right) // 2 & 0xFFFF))
            for left, right in (struct.unpack('<hh', frames[i:i+4]) for i in range(0, len(frames), 4))
        )

    escribir_cabecera_wav(ficCod, {'canales': 1, 'frecuencia': params['frecuencia'], 'bits_per_sample': 32}, len(out_frames))
    
    with open(ficCod, 'ab') as outfile:
        outfile.write(out_frames)

def decEstereo(ficCod, ficEste):
    """
    Decodifica un archivo WAVE de 32 bits en un archivo WAVE estéreo.
    
    Parámetros:
    ficCod (str): Nombre del archivo WAVE codificado de entrada.
    ficEste (str): Nombre del archivo WAVE estéreo de salida.
    """
    params = leer_cabecera_wav(ficCod)
    if params['canales'] != 1 or params['bits_per_sample'] != 32:
        raise ValueError("El archivo de entrada debe ser un archivo WAVE mono con muestras de 32 bits.")
    
    with open(ficCod, 'rb') as infile:
        infile.seek(44)  # Salta la cabecera
        frames = infile.read(params['data_tamaño'])  # Lee los datos de audio

        # Decodifica las muestras de 32 bits en estéreo utilizando comprensiones
        out_frames = bytearray(
            struct.pack(
                '<hh', 
                (semi_sum + (semi_diff - 0x10000 if semi_diff >= 0x8000 else semi_diff)), 
                (semi_sum - (semi_diff - 0x10000 if semi_diff >= 0x8000 else semi_diff))
            )
            for encoded_sample in (struct.unpack('<i', frames[i:i+4])[0] for i in range(0, len(frames), 4))
            for semi_sum, semi_diff in [(encoded_sample >> 16 & 0xFFFF, encoded_sample & 0xFFFF)]
        )

    escribir_cabecera_wav(ficEste, {'canales': 2, 'frecuencia': params['frecuencia'], 'bits_per_sample': 16}, len(out_frames))
    
    with open(ficEste, 'ab') as outfile:
        outfile.write(out_frames)