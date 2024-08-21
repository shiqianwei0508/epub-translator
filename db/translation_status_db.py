import os
import sqlite3


class TranslationStatusDB:
    # 状态常量
    STATUS_PENDING = 0  # 未开始
    STATUS_IN_PROGRESS = 1  # 进行中
    STATUS_COMPLETED = 2  # 完成
    STATUS_ERROR = 3  # 异常退出

    def __init__(self, db_name='translation_status.db', db_directory='.'):
        """初始化 TranslationStatusDB 类。

        :param db_name: 数据库文件名（默认 'translation_status.db'）
        :param db_directory: 数据库文件目录（默认当前目录）
        """
        self.db_name = db_name
        self.db_directory = db_directory
        self.db_path = os.path.join(db_directory, db_name)
        # self.create_tables()
        # self.connection = None
        self.connections = []  # 新增一个列表来存储所有数据库连接

    def connect(self):
        """建立数据库连接"""
        # if self.connection is None:
        #     self.connection = sqlite3.connect(self.db_path)
        #     # 设置WAL模式
        #     self.connection.execute('PRAGMA journal_mode=WAL')
        # return self.connection
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # 设置WAL模式
        conn.execute('PRAGMA journal_mode=WAL')
        self.connections.append(conn)  # 将新连接添加到连接列表
        return conn

    def close_all_connections(self):
        """关闭所有数据库连接"""
        for conn in self.connections:
            try:
                conn.close()  # 关闭连接
            except sqlite3.Error as e:
                print(f"An error occurred while closing a connection: {e}")
        self.connections = []  # 清空连接列表

    # def close(self):
    #     """关闭数据库连接"""
    #     if self.connection:
    #         self.connection.close()
    #         self.connection = None  # 清空连接

    def create_tables(self):
        """创建数据表"""
        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                # 创建翻译状态表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS translation_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chapter_path TEXT NOT NULL,
                        status INTEGER NOT NULL,
                        error_message TEXT
                    )
                ''')
                # 创建状态描述表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS status_description (
                        id INTEGER PRIMARY KEY,
                        description TEXT NOT NULL
                    )
                ''')
                # 插入状态描述
                cursor.execute('DELETE FROM status_description')  # 清空表以避免重复插入
                cursor.executemany('''
                    INSERT INTO status_description (id, description) VALUES (?, ?)
                ''', [
                    (self.STATUS_PENDING, '未开始'),
                    (self.STATUS_IN_PROGRESS, '进行中'),
                    (self.STATUS_COMPLETED, '完成'),
                    (self.STATUS_ERROR, '异常退出')
                ])
                connection.commit()
        except sqlite3.Error as e:
            print(f"An error occurred while creating tables: {e}")

    def insert_status(self, chapter_path, status, error_message=None):
        """插入翻译状态

        :param chapter_path: 章节路径
        :param status: 翻译状态，应为常量
        :param error_message: 错误信息（可选）
        """
        if status not in (self.STATUS_PENDING, self.STATUS_IN_PROGRESS, self.STATUS_COMPLETED, self.STATUS_ERROR):
            raise ValueError("Invalid status value.")

        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('''
                    INSERT INTO translation_status (chapter_path, status, error_message)
                    VALUES (?, ?, ?)
                ''', (chapter_path, status, error_message))
                connection.commit()
        except sqlite3.Error as e:
            print(f"An error occurred while inserting status: {e}")

    def update_status(self, chapter_path, status, error_message=None):
        """更新翻译状态

        :param chapter_path: 章节路径
        :param status: 新的翻译状态，应为常量
        :param error_message: 错误信息（可选）
        """
        if status not in (self.STATUS_PENDING, self.STATUS_IN_PROGRESS, self.STATUS_COMPLETED, self.STATUS_ERROR):
            raise ValueError("Invalid status value.")

        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('''
                    UPDATE translation_status
                    SET status = ?, error_message = ?
                    WHERE chapter_path = ?
                ''', (status, error_message, chapter_path))
                connection.commit()
                if cursor.rowcount == 0:
                    print(f"没有找到章节 '{chapter_path}' 的记录。")
                else:
                    # 查询状态描述
                    cursor.execute('SELECT description FROM status_description WHERE id = ?', (status,))
                    status_description_row = cursor.fetchone()
                    status_description = status_description_row[0] if status_description_row else '未知状态'
                    print(f"章节 '{chapter_path}' 的翻译状态已更新为 '{status_description}'。")
        except sqlite3.Error as e:
            print(f"An error occurred while updating status: {e}")

    def get_all_statuses(self):
        """获取所有翻译状态"""
        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('SELECT * FROM translation_status')
                rows = cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            print(f"An error occurred while fetching statuses: {e}")
            return []

    def get_status_by_chapter(self, chapter_path):
        """根据章节路径获取翻译状态"""
        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('SELECT * FROM translation_status WHERE chapter_path = ?', (chapter_path,))
                row = cursor.fetchone()
            return row
        except sqlite3.Error as e:
            print(f"An error occurred while fetching status for {chapter_path}: {e}")
            return None

    def get_status_descriptions(self):
        """获取所有状态描述"""
        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('SELECT * FROM status_description')
                rows = cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            print(f"An error occurred while fetching status descriptions: {e}")
            return []

    def get_chapters_not_completed(self):
        """获取所有翻译状态不是完成的文章列表"""
        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('SELECT chapter_path FROM translation_status WHERE status != ?',
                               (self.STATUS_COMPLETED,))
                rows = cursor.fetchall()
            return [row[0] for row in rows]  # 返回章节路径列表
        except sqlite3.Error as e:
            print(f"An error occurred while fetching articles not completed: {e}")
            return []

    def __repr__(self):
        return f"<TranslationStatusDB(db_name='{self.db_name}', db_directory='{self.db_directory}')>"
