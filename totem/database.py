"""
Módulo de gerenciamento do banco de dados SQLite
Autor: FrequencyON Team
Data: 2024
"""

import sqlite3
from datetime import datetime
import os
from typing import Optional, List, Dict, Tuple
import threading

class DatabaseManager:
    """Classe responsável por gerenciar todas as operações do banco de dados SQLite"""

    def __init__(self, db_path: str = "frequencyon.db"):
        """
        Inicializa o gerenciador de banco de dados

        Args:
            db_path: Caminho para o arquivo do banco de dados SQLite
        """
        self.db_path = db_path
        self.lock = threading.Lock()  # Lock para operações thread-safe
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """
        Cria uma nova conexão com o banco de dados

        Returns:
            sqlite3.Connection: Conexão com o banco de dados
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self):
        """
        Cria as tabelas necessárias no banco de dados
        """
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Criação da tabela de frequência
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS frequencia (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aluno_id VARCHAR(50) NOT NULL,
                    aluno_nome VARCHAR(100) NOT NULL,
                    data_registro DATE NOT NULL,
                    hora_registro TIME NOT NULL,
                    status_sync INTEGER DEFAULT 0,  -- 0 = não sincronizado, 1 = sincronizado
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(aluno_id, data_registro)  -- Previne duplicidade no mesmo dia
                )
            """)

            # Criação da tabela de alunos (para referência)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alunos (
                    aluno_id VARCHAR(50) PRIMARY KEY,
                    aluno_nome VARCHAR(100) NOT NULL,
                    foto_path VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Índices para melhorar performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_frequencia_data
                ON frequencia(data_registro)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_frequencia_aluno
                ON frequencia(aluno_id)
            """)

            conn.commit()
            conn.close()

            print("✓ Banco de dados inicializado com sucesso")

    def register_attendance(self, aluno_id: str, aluno_nome: str) -> Tuple[bool, str]:
        """
        Registra a presença de um aluno com prevenção de duplicidade

        Args:
            aluno_id: Identificador único do aluno
            aluno_nome: Nome completo do aluno

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()

            try:
                now = datetime.now()
                data_atual = now.strftime("%Y-%m-%d")
                hora_atual = now.strftime("%H:%M:%S")

                # Verifica se já existe registro para este aluno hoje
                cursor.execute("""
                    SELECT id FROM frequencia
                    WHERE aluno_id = ? AND data_registro = ?
                """, (aluno_id, data_atual))

                existing_record = cursor.fetchone()

                if existing_record:
                    return False, f"Aluno {aluno_nome} já registrou presença hoje"

                # Insere novo registro
                cursor.execute("""
                    INSERT INTO frequencia (aluno_id, aluno_nome, data_registro, hora_registro)
                    VALUES (?, ?, ?, ?)
                """, (aluno_id, aluno_nome, data_atual, hora_atual))

                conn.commit()

                print(f"✓ Presença registrada: {aluno_nome} às {hora_atual}")

                # === PONTO DE SINCRONIZAÇÃO FUTURA ===
                # Aqui você deve implementar a lógica para sincronizar
                # com o banco MySQL principal. Sugestões:
                # 1. Criar uma fila de sincronização (Redis, RabbitMQ)
                # 2. Implementar um serviço background que verifica registros com status_sync = 0
                # 3. Enviar os dados via API REST para o servidor principal
                # 4. Atualizar o status_sync para 1 após sincronização bem-sucedida

                return True, f"Presença registrada com sucesso: {aluno_nome}"

            except sqlite3.IntegrityError as e:
                return False, "Erro de integridade no banco de dados"
            except Exception as e:
                return False, f"Erro ao registrar presença: {str(e)}"
            finally:
                conn.close()

    def get_attendance_history(self, limit: int = 50) -> List[Dict]:
        """
        Retorna o histórico de presenças registradas

        Args:
            limit: Número máximo de registros a retornar

        Returns:
            List[Dict]: Lista de registros de presença
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT aluno_id, aluno_nome, data_registro, hora_registro, status_sync
            FROM frequencia
            ORDER BY data_registro DESC, hora_registro DESC
            LIMIT ?
        """, (limit,))

        records = []
        for row in cursor.fetchall():
            records.append({
                'aluno_id': row['aluno_id'],
                'aluno_nome': row['aluno_nome'],
                'data': row['data_registro'],
                'hora': row['hora_registro'],
                'status_sync': row['status_sync']
            })

        conn.close()
        return records

    def get_pending_sync_records(self) -> List[Dict]:
        """
        Retorna registros que ainda não foram sincronizados com o MySQL

        Returns:
            List[Dict]: Lista de registros pendentes de sincronização
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, aluno_id, aluno_nome, data_registro, hora_registro
            FROM frequencia
            WHERE status_sync = 0
            ORDER BY created_at ASC
        """)

        records = []
        for row in cursor.fetchall():
            records.append({
                'id': row['id'],
                'aluno_id': row['aluno_id'],
                'aluno_nome': row['aluno_nome'],
                'data': row['data_registro'],
                'hora': row['hora_registro']
            })

        conn.close()
        return records

    def mark_as_synced(self, record_id: int):
        """
        Marca um registro como sincronizado

        Args:
            record_id: ID do registro no banco local
        """
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE frequencia
                SET status_sync = 1
                WHERE id = ?
            """, (record_id,))

            conn.commit()
            conn.close()
