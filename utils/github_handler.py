"""
Handler para interação com GitHub
Permite ler e atualizar arquivos de tabelas no repositório
"""
import requests
import base64
from typing import Optional, Tuple

class GitHubHandler:
    def __init__(self, token: str, repo: str):
        """
        Inicializa o handler do GitHub
        
        Args:
            token: Personal access token do GitHub
            repo: Repositório no formato "usuario/repo"
        """
        self.token = token
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{repo}/contents"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def get_file(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Obtém o conteúdo de um arquivo do GitHub
        
        Args:
            file_path: Caminho do arquivo no repo (ex: "data/tabelas/premierleague.txt")
        
        Retorna:
            (conteúdo: str, sha: str) ou (None, None) se erro
        """
        url = f"{self.base_url}/{file_path}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            sha = data['sha']
            
            return content, sha
        
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar arquivo: {e}")
            return None, None
    
    def update_file(self, file_path: str, content: str, 
                   commit_message: str, sha: str) -> bool:
        """
        Atualiza um arquivo no GitHub
        
        Args:
            file_path: Caminho do arquivo no repo
            content: Novo conteúdo do arquivo
            commit_message: Mensagem do commit
            sha: SHA do arquivo atual (necessário para atualizar)
        
        Retorna:
            True se sucesso, False se erro
        """
        url = f"{self.base_url}/{file_path}"
        
        # Encode content to base64
        content_encoded = base64.b64encode(content.encode()).decode()
        
        data = {
            "message": commit_message,
            "content": content_encoded,
            "sha": sha
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            return True
        
        except requests.exceptions.RequestException as e:
            print(f"Erro ao atualizar arquivo: {e}")
            return False
    
    def create_file(self, file_path: str, content: str, 
                   commit_message: str) -> bool:
        """
        Cria um novo arquivo no GitHub
        
        Args:
            file_path: Caminho do arquivo no repo
            content: Conteúdo do arquivo
            commit_message: Mensagem do commit
        
        Retorna:
            True se sucesso, False se erro
        """
        url = f"{self.base_url}/{file_path}"
        
        # Encode content to base64
        content_encoded = base64.b64encode(content.encode()).decode()
        
        data = {
            "message": commit_message,
            "content": content_encoded
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            return True
        
        except requests.exceptions.RequestException as e:
            print(f"Erro ao criar arquivo: {e}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """
        Verifica se um arquivo existe no repositório
        
        Args:
            file_path: Caminho do arquivo no repo
        
        Retorna:
            True se existe, False caso contrário
        """
        url = f"{self.base_url}/{file_path}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return response.status_code == 200
        
        except requests.exceptions.RequestException:
            return False
    
    @staticmethod
    def get_raw_url(repo: str, file_path: str, branch: str = "main") -> str:
        """
        Retorna a URL raw de um arquivo no GitHub
        
        Args:
            repo: Repositório no formato "usuario/repo"
            file_path: Caminho do arquivo
            branch: Branch (padrão: main)
        
        Retorna:
            URL completa do arquivo raw
        """
        return f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"
