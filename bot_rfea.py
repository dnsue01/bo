from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import asyncio

# Configura el token de tu bot de Telegram
TOKEN = "7941997835:AAGFA-bMzJjQbgRFzFh9KpLpJgqfw3K4S38"

# Configura el servicio de ChromeDriver
CHROME_DRIVER_PATH = "./chromedriver.exe"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Hola! Envíame tu correo y contraseña con este formato:\n"
        "`correo:tu_correo@example.com contraseña:tu_contraseña` 🏃",
        parse_mode="Markdown"
    )

async def handle_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    if "correo:" in user_message and "contraseña:" in user_message:
        loading_message = await update.message.reply_text("⚙️ Preparándote para el calentamiento... ¡Aguarda un momento! ⏳")
        try:
            correo = user_message.split("correo:")[1].split("contraseña:")[0].strip()
            contraseña = user_message.split("contraseña:")[1].strip()

            context.user_data["correo"] = correo
            context.user_data["contraseña"] = contraseña

            service = Service(CHROME_DRIVER_PATH)
            driver = webdriver.Chrome(service=service)
            driver.get("https://atletismorfea.es/user/login-registro")
            time.sleep(3)

            try:
                accept_cookies_button = driver.find_element(By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                accept_cookies_button.click()
            except:
                pass

            driver.find_element(By.ID, "edit-email").send_keys(correo)
            driver.find_element(By.ID, "edit-password").send_keys(contraseña)
            driver.find_element(By.ID, "edit-submit").click()
            time.sleep(5)

            try:
                driver.find_element(By.XPATH, '//div[contains(@class, "alert-danger") and contains(@role, "alert")]')
                await context.bot.delete_message(chat_id=update.message.chat_id, message_id=loading_message.message_id)
                await update.message.reply_text("❌ Credenciales incorrectas. Por favor, inténtalo de nuevo enviando tus datos.")
                driver.quit()
                return
            except:
                pass

            driver.maximize_window()
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[text()="Mis inscripciones"]'))
            ).click()
            time.sleep(5)

            context.user_data["driver"] = driver
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=loading_message.message_id)
            await update.message.reply_text("✅ Sesión iniciada con éxito. ¡Bienvenido a la pista! 🏟️")
            await mostrar_menu(update)
        except:
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=loading_message.message_id)
            await update.message.reply_text("⚠️ Ocurrió un problema. Por favor, inténtalo de nuevo más tarde.")
    else:
        await update.message.reply_text(
            "❗ El formato es incorrecto. Por favor, envíamelo como:\n"
            "`correo:tu_correo@example.com contraseña:tu_contraseña` 📩",
            parse_mode="Markdown"
        )

def seleccionar_competicion(driver, opcion_index):
    mensaje = []
    try:
        opciones = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//ul[@class="select2-results__options"]/li'))
        )
        if opcion_index <= len(opciones):
            opcion_seleccionada_texto = opciones[opcion_index - 1].text
            opciones[opcion_index - 1].click()
            mensaje.append(f"Se seleccionó la competición: {opcion_seleccionada_texto}")
        else:
            mensaje.append("Índice de competición fuera de rango.")
            return None, mensaje

        
        time.sleep(20)

        
        checkboxes = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//div[@class="panel-body"]//div[contains(@class, "form-type-checkbox")]'))
        )
        
        mensaje.append("\nPruebas disponibles:")
        for i, checkbox in enumerate(checkboxes, 1):
            try:
                label = checkbox.find_element(By.TAG_NAME, 'label')
                prueba_nombre = label.text
                mensaje.append(f"{i}. {prueba_nombre}")
            except Exception as e:
                mensaje.append(f"Error al procesar prueba {i}: {str(e)}")
                continue

        return checkboxes, mensaje

    except TimeoutException as e:
        mensaje.append(f"Error de tiempo de espera: {str(e)}")
        return None, mensaje
    except Exception as e:
        mensaje.append(f"Error inesperado: {str(e)}")
        return None, mensaje

def get_main_menu_markup():
    keyboard = [
        [InlineKeyboardButton("1. Inscribirse", callback_data="inscribirse")],
        [InlineKeyboardButton("2. Ver inscripciones", callback_data="ver_inscripciones")],
        [InlineKeyboardButton("Salir", callback_data="salir")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def ver_inscripciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    driver = context.user_data.get("driver")
    inscripciones = procesar_inscripciones(driver)
    if not inscripciones:
        # Si no hay inscripciones, mostramos el menú principal
        reply_markup = get_main_menu_markup()
        await query.message.reply_text(
            "📝 No tienes inscripciones activas. ⚡ Elige tu próximo paso en la pista:",
            reply_markup=reply_markup
        )
        return

    # Si hay inscripciones, se muestran en formato interactivo
    keyboard = []
    for i, insc in enumerate(inscripciones, 1):
        text = f"{i}. 📅 {insc['fecha']} - 🏆 {insc['competicion']} ({insc['prueba']})"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"ver_inscripcion-{insc['id']}")])
        keyboard.append([InlineKeyboardButton(f"❌ Dar de baja inscripción {i}", callback_data=f"baja-{insc['id']}")])
    keyboard.append([InlineKeyboardButton("↩️ Volver al menú principal", callback_data="menu_principal")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "📋 Tus inscripciones actuales:\nSelecciona una inscripción para ver más detalles o darla de baja:",
        reply_markup=reply_markup
    )

def procesar_inscripciones(driver):
    inscripciones = []
    try:
        table = driver.find_element(By.CLASS_NAME, "tabla_inscripciones")
        rows = table.find_elements(By.TAG_NAME, "tr")
        for row in rows[1:]:
            columns = row.find_elements(By.TAG_NAME, "td")
            delete_link = None
            try:
                delete_link = columns[-1].find_element(By.TAG_NAME, "a").get_attribute("href")
            except:
                pass
            if delete_link and "/user/inscription/delete/" in delete_link:
                inscription_id = delete_link.split("/")[-2]
                inscripciones.append({
                    'fecha': columns[0].text,
                    'competicion': columns[1].text,
                    'prueba': columns[2].text,
                    'id': inscription_id,
                    'delete_link': delete_link
                })
    except Exception as e:
        print(f"Error procesando inscripciones: {e}")
    return inscripciones

async def mostrar_menu(update: Update):
    reply_markup = get_main_menu_markup()
    await update.message.reply_text("¿Qué deseas hacer?", reply_markup=reply_markup)

def dividir_competiciones(competiciones, tamaño_pagina=5):
    """Divide una lista de competiciones en páginas de tamaño fijo."""
    return [competiciones[i:i + tamaño_pagina] for i in range(0, len(competiciones), tamaño_pagina)]

async def mostrar_pagina_competiciones(update: Update, context: ContextTypes.DEFAULT_TYPE, pagina):
    """Muestra una página específica de competiciones."""
    competiciones = context.user_data.get("competiciones", [])
    if not competiciones or pagina < 1 or pagina > len(competiciones):
        await update.callback_query.message.reply_text("No hay competiciones disponibles o la página es inválida.")
        return

    context.user_data["pagina_actual"] = pagina
    pagina_actual = competiciones[pagina - 1]

    keyboard = [
        [InlineKeyboardButton(f"{i}. {comp[1].text[:50]}...", callback_data=f"comp-{comp[0]}")]
        for i, comp in enumerate(pagina_actual, 1)
    ]

    if pagina > 1:
        keyboard.append([InlineKeyboardButton("⬅️ Página Anterior", callback_data=f"pagina-{pagina - 1}")])
    if pagina < len(competiciones):
        keyboard.append([InlineKeyboardButton("➡️ Página Siguiente", callback_data=f"pagina-{pagina + 1}")])

    keyboard.append([InlineKeyboardButton("↩️ Volver al menú principal", callback_data="menu_principal")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text(
        f"Selecciona una competición (Página {pagina}/{len(competiciones)}):",
        reply_markup=reply_markup
    )

async def handle_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    driver = context.user_data.get("driver")

    if query.data == "ver_inscripciones":
        await query.edit_message_text("🔍 Consultando tus inscripciones... ¡Un momento! ⏳")
        await ver_inscripciones(update, context)

    elif query.data.startswith("baja-"):
        inscripcion_id = query.data.split("-")[1]
        await query.edit_message_text("⏳ Procesando la baja de tu inscripción...")
        reply_markup = await dar_baja_inscripcion(driver, inscripcion_id)
        if reply_markup:
            await query.message.reply_text(
                "⚠️ ¿Estás seguro de que quieres darte de baja de esta inscripción?",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("❌ No se pudo abrir el diálogo de confirmación. Intenta más tarde.")

    elif query.data.startswith("confirmar_baja-"):
        inscripcion_id = query.data.split("-")[1]
        await query.edit_message_text("⏳ Procesando la baja...")

        if await dar_baja_inscripcion(driver, inscripcion_id, confirmar=True):
            await query.message.reply_text("✅ Te has dado de baja correctamente de la inscripción.")
        else:
            await query.message.reply_text("❌ No se pudo procesar la baja. Por favor, intenta más tarde.")
        await mostrar_inscripciones(update, context)

    elif query.data == "menu_principal":
        try:
            # Realizar clic en "Mis inscripciones" en el navegador
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[text()="Mis inscripciones"]'))
            ).click()
            time.sleep(5)

            # Mostrar el menú principal al usuario
            reply_markup = get_main_menu_markup()
            await query.message.reply_text("⚡ Elige tu próximo paso en la pista:", reply_markup=reply_markup)
        except Exception as e:
            await query.message.reply_text(f"⚠️ Ocurrió un problema al volver al menú principal: {e}")

    elif query.data == "inscribirse":
        await query.edit_message_text("Iniciando inscripción...")
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "edit-registro"))
            ).click()
            time.sleep(3)

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//span[@role="combobox"]'))
            ).click()
            time.sleep(3)

            options = driver.find_elements(By.XPATH, '//ul[@class="select2-results__options"]/li')
            competiciones = {i + 1: option for i, option in enumerate(options)}

            context.user_data["competiciones"] = dividir_competiciones(list(competiciones.items()))
            await mostrar_pagina_competiciones(update, context, pagina=1)
        except Exception as e:
            await query.edit_message_text(f"Ocurrió un error: {e}")
            await query.message.reply_text("¿Qué deseas hacer?", reply_markup=get_main_menu_markup())

    elif query.data.startswith("pagina-"):
        pagina = int(query.data.split("-")[1])
        await mostrar_pagina_competiciones(update, context, pagina)

    elif query.data.startswith("comp-"):
        seleccion = int(query.data.split("-")[1])
        competiciones = context.user_data.get("competiciones")
        if competiciones:
            try:
                checkboxes, mensajes = seleccionar_competicion(driver, seleccion)
                mensaje_completo = "\n".join(mensajes)
                await query.message.reply_text(mensaje_completo)

                # Crear los botones en líneas de 4
                keyboard = []
                for i, checkbox in enumerate(checkboxes, 1):
                    if (i - 1) % 4 == 0:
                        keyboard.append([])  # Nueva fila cada 4 elementos
                    keyboard[-1].append(InlineKeyboardButton(f"{i}", callback_data=f"prueba-{i-1}"))

                # Botón para volver al menú principal
                keyboard.append([InlineKeyboardButton("Volver al menú principal", callback_data="menu_principal")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(
                    "Selecciona el número de la prueba en la que quieres inscribirte:",
                    reply_markup=reply_markup
                )
            except Exception as e:
                await query.edit_message_text(f"Ocurrió un error: {e}")
        else:
            await query.edit_message_text("Selección inválida. Por favor, intenta nuevamente.")

    elif query.data == "salir":
        if driver:
            driver.quit()
        await query.edit_message_text("Has salido del menú. ¡Hasta luego!")




def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_credentials))
    application.add_handler(CallbackQueryHandler(handle_option))

    application.run_polling()

if __name__ == "__main__":
    main()