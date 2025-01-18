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

def get_main_menu_markup():
    keyboard = [
        [InlineKeyboardButton("1️⃣ Inscribirse 📝", callback_data="inscribirse")],
        [InlineKeyboardButton("2️⃣ Ver inscripciones 👀", callback_data="ver_inscripciones")],
        [InlineKeyboardButton("❌ Salir", callback_data="salir")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def mostrar_menu(update: Update):
    reply_markup = get_main_menu_markup()
    await update.message.reply_text("⚡ Elige tu próximo paso en la pista:", reply_markup=reply_markup)

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

async def dar_baja_inscripcion(driver, inscripcion_id, confirmar=True):
  
    try:
        # Hacer clic en el botón de eliminar correspondiente a la inscripción
        delete_button = driver.find_element(By.XPATH, f'//a[contains(@href, "/user/inscription/delete/{inscripcion_id}/")]')
        delete_button.click()

        # Esperar a que aparezca el diálogo de confirmación
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ui-dialog"))
        )

        # Elegir entre Confirmar o Cancelar
        if confirmar:
            # Clic en el botón de confirmar
            confirm_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "button--primary")]'))
            )
            confirm_button.click()
        else:
            # Clic en el botón de cancelar
            cancel_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "dialog-cancel")]'))
            )
            cancel_button.click()

        # Esperar un momento para asegurarse de que la acción se complete
        time.sleep(2)
        return True
    except Exception as e:
        print(f"Error procesando el diálogo de confirmación: {e}")
        return False


async def mostrar_inscripciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    driver = context.user_data.get("driver")
    inscripciones = procesar_inscripciones(driver)
    if not inscripciones:
        await update.callback_query.message.reply_text("📝 No tienes inscripciones activas.")
        return
    keyboard = []
    for i, insc in enumerate(inscripciones, 1):
        text = f"{i}. 📅 {insc['fecha']} - 🏆 {insc['competicion']} ({insc['prueba']})"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"ver_inscripcion-{insc['id']}")])
        keyboard.append([InlineKeyboardButton(f"❌ Dar de baja inscripción {i}", callback_data=f"baja-{insc['id']}")])
    keyboard.append([InlineKeyboardButton("↩️ Volver al menú principal", callback_data="menu_principal")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        "📋 Tus inscripciones actuales:\nSelecciona una inscripción para ver más detalles o darla de baja:",
        reply_markup=reply_markup
    )

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


def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_credentials))
    application.add_handler(CallbackQueryHandler(handle_option))
    application.run_polling()

if __name__ == "__main__":
    main()
