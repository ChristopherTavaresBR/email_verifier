# google_verifier.py
from selenium.webdriver.support import expected_conditions as EC
from application.base_verifier import BaseEmailVerifier

class GoogleEmailVerifier(BaseEmailVerifier):
    def verify_email(self, email: str) -> bool:
        try:
            if not self.driver:
                self.logger.error("Driver não inicializado")
                return False
                
            # Acessa a página de criação de conta
            self.driver.get(self.config.get_verification_url())
            self.logger.info(f"Acessando URL: {self.config.get_verification_url()}")

            # Step 1: Preenche o nome
            self.inputer_text(self.config.selector_step_one, self.email_text.name, '1')
            self.logger.info("Nome adicionado #step 1...")
            self.click_button(self.config.selector_button_step_one, '1')

            # Step 2: Preenche data de nascimento e gênero
            self.logger.info(f"Step 2/{self.config.total_steps}...")
            self.inputer_text(self.config.selector_step_two_day, self.email_text.day_birthday, '2')
            self.inputer_text(self.config.selector_step_two_month, self.email_text.month_birthday, '2')
            self.inputer_text(self.config.selector_step_two_year, self.email_text.year_birthday, '2')
            self.inputer_text(self.config.selector_step_two_gender, self.email_text.gender, '2')
            self.logger.info("Gênero e nascimento adicionados...")
            self.click_button(self.config.selector_button_step_two, '2')

            # Step 3: Seleciona sugestão de email
            self.logger.info("Aguardando seletor de sugestão de email...")
            self.click_button(self.config.selector_sugester_email, '3')

            # Verifica o email
            self.logger.info(f"Verificando email: {email}@gmail.com...")
            self.inputer_text(self.config.selector_input_email, email, 'Verify', True)
            self.click_button(self.config.selector_button_next_email, "verify")

            # Verifica se há mensagem de erro (email disponível)
            is_available = self.verify_element_exists(self.config.selector_message_email, 2)
            
            if not is_available:
                self.driver.back()  # Volta para tentar outro email se necessário
            
            return is_available

        except Exception as e:
            self.logger.error(f"Erro durante a verificação do email: {e}")
            return False

    def _process_verification_queue(self):
        """
        Processa a fila de verificação de emails.
        Sobrescreve o método da classe base para adicionar lógica específica do Google.
        """
        try:
            while True:
                # Verifica se há emails para processar
                email = self.queues.email_queue.get()
                
                # Realiza a verificação
                result = self.verify_email(email)
                
                # Coloca o resultado na fila
                self.queues.result_queue.put({email: result})
                
                # Atualiza o status de atividade
                self.update_last_activity()
                
        except Exception as e:
            self.logger.error(f"Erro no processamento da fila: {e}")
            self.queues.result_queue.put({"error": str(e)})

    def update_last_activity(self):
        """Atualiza o timestamp da última atividade"""
        if hasattr(self, 'last_activity_callback'):
            self.last_activity_callback()