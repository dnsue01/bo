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
        "¡Hola! Envíame tu correo y contraseña con este formato:\n"
        "`correo:tu_correo@example.com contraseña:tu_contraseña`",
        parse_mode="Markdown"
    )

async def handle_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    if "correo:" in user_message and "contraseña:" in user_message:
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

            driver.maximize_window()
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[text()="Mis inscripciones"]'))
            ).click()
            print("Se hizo clic en 'Mis inscripciones'.")
            time.sleep(5)

            context.user_data["driver"] = driver

            await mostrar_menu(update)
        except Exception as e:
            await update.message.reply_text(f"Ocurrió un error: {e}")
    else:
        await update.message.reply_text(
            "El formato es incorrecto. Por favor, envíamelo como:\n"
            "`correo:tu_correo@example.com contraseña:tu_contraseña`",
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

async def mostrar_menu(update: Update):
    reply_markup = get_main_menu_markup()
    await update.message.reply_text("¿Qué deseas hacer?", reply_markup=reply_markup)

async def handle_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    driver = context.user_data.get("driver")

    if query.data == "ver_inscripciones":
        await query.edit_message_text("🔍 Consultando tus inscripciones... ¡Un momento! ⏳")
        await mostrar_inscripciones(update, context)

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

    elif query.data == "cancelar_baja":
        inscripcion_id = query.data.split("-")[1]
        await query.edit_message_text("⏳ Cancelando la operación...")

        if await dar_baja_inscripcion(driver, inscripcion_id, confirmar=False):
            await query.message.reply_text("❌ Operación cancelada correctamente.")
        else:
            await query.message.reply_text("⚠️ No se pudo cancelar la operación. Intenta más tarde.")
        await mostrar_inscripciones(update, context)

    elif query.data == "menu_principal":
        reply_markup = get_main_menu_markup()
        await query.message.reply_text("⚡ Elige tu próximo paso en la pista:", reply_markup=reply_markup)

    # Added "inscribirse" functionality
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

            context.user_data["competiciones"] = competiciones

            keyboard = [
                [InlineKeyboardButton(f"{i}. {option.text[:50]}...", callback_data=f"comp-{i}")]
                for i, option in competiciones.items()
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Selecciona una competición:", reply_markup=reply_markup)
        except Exception as e:
            await query.edit_message_text(f"Ocurrió un error: {e}")
            if hasattr(update, 'message'):
                await mostrar_menu(update)
            else:
                await query.message.reply_text("¿Qué deseas hacer?", reply_markup=get_main_menu_markup())

    elif query.data.startswith("comp-"):
        seleccion = int(query.data.split("-")[1])
        competiciones = context.user_data.get("competiciones")
        if competiciones and seleccion in competiciones:
            try:
                checkboxes, mensajes = seleccionar_competicion(driver, seleccion)
                mensaje_completo = "\n".join(mensajes)
                await query.message.reply_text(mensaje_completo)

                if checkboxes:
                    context.user_data["checkboxes"] = checkboxes
                    keyboard = []
                    for i, checkbox in enumerate(checkboxes, 1):
                        label = checkbox.find_element(By.TAG_NAME, 'label')
                        prueba_nombre = label.text
                        if i % 2 == 1:
                            keyboard.append([])
                        keyboard[-1].append(InlineKeyboardButton(
                            f"{i}", 
                            callback_data=f"prueba-{i-1}"
                        ))
                    
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