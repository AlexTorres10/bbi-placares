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
            response = requests.get(url, headers=self.headers, timeout=10)
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
            response = requests.put(url, headers=self.headers, json=data, timeout=10)
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
            response = requests.put(url, headers=self.headers, json=data, timeout=10)
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
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200

        except requests.exceptions.RequestException:
            return False
    
    def update_files(self, files: list, message: str, branch: str = "main") -> bool:
        """
        Commita múltiplos arquivos em um único commit via Git Trees API.

        Args:
            files: lista de dicts com {"path": str, "content": str}
            message: mensagem do commit
            branch: branch alvo (padrão: "main")

        Retorna:
            True se sucesso, False se erro
        """
        api_base = f"https://api.github.com/repos/{self.repo}"
        try:
            # 1. SHA do commit HEAD
            ref_resp = requests.get(
                f"{api_base}/git/ref/heads/{branch}", headers=self.headers, timeout=10
            )
            ref_resp.raise_for_status()
            head_sha = ref_resp.json()["object"]["sha"]

            # 2. SHA da árvore atual
            commit_resp = requests.get(
                f"{api_base}/git/commits/{head_sha}", headers=self.headers, timeout=10
            )
            commit_resp.raise_for_status()
            base_tree_sha = commit_resp.json()["tree"]["sha"]

            # 3. Criar nova árvore
            tree_entries = [
                {"path": f["path"], "mode": "100644", "type": "blob", "content": f["content"]}
                for f in files
            ]
            tree_resp = requests.post(
                f"{api_base}/git/trees",
                headers=self.headers,
                json={"base_tree": base_tree_sha, "tree": tree_entries},
                timeout=10,
            )
            tree_resp.raise_for_status()
            new_tree_sha = tree_resp.json()["sha"]

            # 4. Criar novo commit
            new_commit_resp = requests.post(
                f"{api_base}/git/commits",
                headers=self.headers,
                json={"message": message, "tree": new_tree_sha, "parents": [head_sha]},
                timeout=10,
            )
            new_commit_resp.raise_for_status()
            new_commit_sha = new_commit_resp.json()["sha"]

            # 5. Atualizar referência do branch
            patch_resp = requests.patch(
                f"{api_base}/git/refs/heads/{branch}",
                headers=self.headers,
                json={"sha": new_commit_sha},
                timeout=10,
            )
            patch_resp.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            print(f"Erro ao criar commit multi-arquivo: {e}")
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
