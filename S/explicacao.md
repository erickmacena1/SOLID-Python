# Análise do "S" do SOLID: `bad_src.py` → `main.py` + módulos

## 1. O que é o SRP (Single Responsibility Principle)

O **S** do SOLID é o **Princípio da Responsabilidade Única**. A definição clássica, de Robert C. Martin (Uncle Bob), é:

> **"Uma classe deve ter um, e apenas um, motivo para mudar."**

"Responsabilidade" aqui não quer dizer "fazer uma coisa só" no sentido de ter um único método. Quer dizer que o código deve atender a **uma única fonte de mudança**. Se dois motivos diferentes podem obrigar você a mexer na mesma classe, ela tem responsabilidades demais.

Um jeito prático de testar: tente descrever a classe em uma frase. Se aparecer um **"e"** ("ela busca dados **e** formata **e** imprime"), provavelmente o SRP está sendo violado.

---

## 2. O problema no `bad_src.py`

Em [bad_src.py](bad_src.py), a classe `ListRepositories` junta **quatro responsabilidades diferentes**:

| # | Responsabilidade | Onde está no `bad_src.py` | Motivo para mudar |
|---|---|---|---|
| 1 | **Comunicação HTTP com a API do GitHub** | [bad_src.py:5](bad_src.py#L5) e [bad_src.py:10-15](bad_src.py#L10-L15): `API_BASE_URL` e `get_repos_by_user()` | A URL da API muda, o GitHub pede autenticação, você troca `requests` por `httpx`, quer paginação... |
| 2 | **Interpretar os dados** (transformar o JSON cru em algo útil) | [bad_src.py:17-23](bad_src.py#L17-L23): `parse_response()` lendo `body[i]["id"]`, `["name"]`, `["stargazers_count"]` | O formato do JSON muda, você quer outros campos... |
| 3 | **Apresentar os dados** (saída no console) | [bad_src.py:22-23](bad_src.py#L22-L23): o `print(...)` dentro do `parse_response()` | Você quer mostrar em outro formato, gravar num arquivo, devolver numa API web... |
| 4 | **Orquestrar o fluxo / ponto de entrada** | [bad_src.py:26-27](bad_src.py#L26-L27): instancia a classe e chama o método no nível do módulo, e [bad_src.py:18](bad_src.py#L18): `parse_response()` chama `get_repos_by_user()` por conta própria | Muda a ordem das etapas, o usuário passa a vir de um argumento de linha de comando... |

Há ainda uma **quinta responsabilidade escondida**: o "conceito" de repositório (id, nome, estrelas) não existe em lugar nenhum. Ele aparece só como chaves de dicionário espalhadas numa f-string.

O ponto mais grave é o [bad_src.py:18](bad_src.py#L18). O método `parse_response()` **chama** `get_repos_by_user()` internamente, então "interpretar" fica acoplado a "buscar". Não dá para testar o parser sem fazer uma requisição HTTP real, nem reaproveitá-lo com dados de outra origem (um arquivo JSON, um mock, um cache).

Outro detalhe: quando dá erro (status ≠ 200), o `parse_response()` simplesmente **não faz nada**, e a mensagem de erro é descartada em silêncio. Isso acontece porque ninguém é claramente responsável por decidir o que fazer em caso de erro.

---

## 3. Como cada parte foi separada

### 3.1 `API_BASE_URL` + `get_repos_by_user()` → [github/client.py](github/client.py)

**Antes** ([bad_src.py:4-15](bad_src.py#L4-L15)):
```python
class ListRepositories():
    API_BASE_URL = 'https://api.github.com'
    def __init__(self, user):
        self._user = user
    def get_repos_by_user(self):
        response = requests.get(f'{self.API_BASE_URL}/users/{self._user}/repos')
        ...
```

**Depois** ([github/client.py:4-13](github/client.py#L4-L13)):
```python
class GithubClient():
    API_BASE_URL = 'https://api.github.com'
    @classmethod
    def get_repos_by_user(self, user):
        response = requests.get(f'{self.API_BASE_URL}/users/{user}/repos')
        ...
```

**Por que separar:** essa parte tem **uma única responsabilidade: conversar com a API do GitHub.** Ela sabe a URL, sabe usar o `requests` e sabe interpretar o `status_code`. Não sabe nada de impressão nem do que é um "Repo".

Pontos importantes da mudança:

- **O nome mudou de `ListRepositories` para `GithubClient`.** O nome antigo descrevia uma *tarefa* (listar repositórios, que envolve buscar + formatar + imprimir). O novo descreve um *papel* (cliente da API do GitHub). Nomes que descrevem papéis costumam indicar classes mais coesas.
- **O `user` deixou de ser estado da classe (`self._user`) e virou parâmetro do método.** O cliente não precisa "pertencer" a um usuário, e o mesmo cliente pode buscar repositórios de qualquer um. Com isso o método virou `@classmethod`, já que não há estado por instância.
- **O pacote `github/` isola tudo que é específico do GitHub.** Se amanhã você precisar de `get_user_info()` ou `get_commits()`, é aqui que isso entra, e **só aqui**.

**Único motivo para mudar:** a forma de se comunicar com o GitHub.

---

### 3.2 O "conceito" de repositório → [models/repo.py](models/repo.py)

**Antes:** não existia. O repositório era só um dicionário cru, e as chaves `"id"`, `"name"` e `"stargazers_count"` ficavam espalhadas na f-string do [bad_src.py:23](bad_src.py#L23).

**Depois** ([models/repo.py:1-21](models/repo.py#L1-L21)):
```python
class Repo():
    def __init__(self, id, name, stars):
        ...
    def __str__(self):
        return f'id: {self._id} name: {self._name} stars: {self._stars}'
```

**Por que separar:** essa é a **entidade de domínio**, ou seja, a representação do que é um repositório *para a sua aplicação*, independente de onde os dados vieram. A responsabilidade dela é **guardar os dados de um repositório e definir como ele se representa como texto** (`__str__`).

Repare numa tradução sutil: a API chama o campo de `stargazers_count`, mas o modelo chama de `stars`. O modelo usa a **linguagem da sua aplicação**, não a da API. Se o GitHub renomear o campo, o `Repo` continua igual, e só quem faz a conversão (o parser) precisa mudar.

A pasta `models/` é uma convenção comum para guardar entidades de domínio, separadas da infraestrutura (HTTP) e da lógica de conversão.

**Único motivo para mudar:** o que a aplicação considera ser um repositório (por exemplo, passar a guardar também a linguagem ou a descrição).

---

### 3.3 `parse_response()` → [repo/parser.py](repo/parser.py)

**Antes** ([bad_src.py:17-23](bad_src.py#L17-L23)):
```python
def parse_response(self):
    response = self.get_repos_by_user()   # busca os dados (!)
    body = response['body']
    if response['status_code'] == 200:    # trata o status HTTP (!)
        for i in range(len(body)):
            print(f'{body[i]["id"]} - ...')  # formata e imprime (!)
```

**Depois** ([repo/parser.py:3-9](repo/parser.py#L3-L9)):
```python
class RepoParser():
    @classmethod
    def parse(cls, response):
        for i in range(len(response)):
            repo = response[i]
            repo = Repo(repo['id'], repo['name'], repo['stargazers_count'])
            print(repo)
```

**Por que separar:** a responsabilidade do parser é **converter o dado cru (lista de dicionários) em objetos `Repo`.** É a "ponte" entre o formato da API e o modelo da aplicação.

O que mudou em relação ao original:

1. **Ele não busca mais os dados.** Recebe `response` (a lista já pronta) por parâmetro. Essa é a mudança mais importante, porque o parser ficou **desacoplado do HTTP**. Você pode testá-lo passando uma lista qualquer:
   ```python
   RepoParser.parse([{"id": 1, "name": "teste", "stargazers_count": 5}])
   ```
   Nenhuma requisição de rede é necessária.
2. **Ele não verifica mais o `status_code`.** Isso é assunto do HTTP, e o parser não deveria nem saber que existe HTTP.
3. **A formatação do texto saiu dele** e foi para o `__str__` do `Repo`. O parser só faz `print(repo)`.

---

### 3.4 Execução no nível do módulo → [main.py](main.py)

**Antes** ([bad_src.py:26-27](bad_src.py#L26-L27)):
```python
repos = ListRepositories('erickmacena1')
repos.parse_response()
```

**Depois** ([main.py:4-11](main.py#L4-L11)):
```python
if __name__ == '__main__':
    username = 'rafaelcamarda'
    response = GithubClient.get_repos_by_user(username)

    if response['status_code'] == 200:
        RepoParser.parse(response['body'])
    else:
        print(response['body'])
```

**Por que separar:** o `main.py` é o **orquestrador** (às vezes chamado de *composition root*). Sua única responsabilidade é **coordenar o fluxo**: chamar o cliente, decidir o que fazer com o resultado e acionar o parser. Ele não sabe *como* buscar dados nem *como* convertê-los, só sabe *em que ordem* as coisas acontecem.

Três ganhos:

- **Os módulos não se conhecem desnecessariamente.** O `GithubClient` não conhece o `RepoParser`, e o `RepoParser` não conhece o `GithubClient`. Quem liga os dois é o `main.py`. No `bad_src.py` essa ligação estava escondida *dentro* da classe ([bad_src.py:18](bad_src.py#L18)).
- **O tratamento de erro ganhou um dono.** Agora o `else: print(response['body'])` mostra a mensagem de erro, que antes era descartada.
- **O `if __name__ == '__main__':`** faz o código só rodar quando o arquivo é executado diretamente, e não quando é importado. No `bad_src.py`, qualquer `import bad_src` dispararia uma requisição HTTP, um efeito colateral indesejado.

**Único motivo para mudar:** o fluxo da aplicação (a ordem das etapas, a origem do `username`, o que fazer em caso de erro).

---

## 4. Resumo do mapeamento

```
bad_src.py (ListRepositories)                    Versão refatorada
─────────────────────────────────                ──────────────────────────────────
API_BASE_URL + get_repos_by_user()      ──────►  github/client.py   → GithubClient
                                                 (comunicação HTTP)

dicionário cru + chaves na f-string     ──────►  models/repo.py     → Repo
                                                 (entidade de domínio + __str__)

parse_response() (parte da conversão)   ──────►  repo/parser.py     → RepoParser
                                                 (dict → Repo)

parse_response() (chamada ao HTTP       ──────►  main.py
  + checagem do status_code)                     (orquestração + tratamento de erro)
linhas 26-27 (execução)
```

| Módulo | Responsabilidade única | Só muda quando... |
|---|---|---|
| `github/client.py` | Falar com a API do GitHub | a API ou a forma de acessá-la muda |
| `models/repo.py` | Representar um repositório | o conceito de repositório muda |
| `repo/parser.py` | Converter JSON cru em `Repo` | o formato dos dados de entrada muda |
| `main.py` | Orquestrar o fluxo | o fluxo da aplicação muda |

---

## 5. Pontos críticos da versão refatorada

Mesmo a versão "boa" tem pontos que valem discussão, e perceber isso ajuda a fixar o conceito.

### 5.1 O `RepoParser` ainda tem duas responsabilidades
Em [repo/parser.py:9](repo/parser.py#L9), o parser **converte e imprime**. Pela frase do "e", isso ainda viola o SRP. Uma versão mais fiel ao princípio **retornaria** a lista, e quem decide imprimir seria o `main.py` (ou uma classe de apresentação):

```python
# repo/parser.py
class RepoParser():
    @classmethod
    def parse(cls, response):
        return [Repo(r['id'], r['name'], r['stargazers_count']) for r in response]

# main.py
repos = RepoParser.parse(response['body'])
for repo in repos:
    print(repo)
```

Assim, se você quisesse gravar os repositórios num CSV em vez de imprimir, o parser não precisaria mudar.

### 5.2 Bug nas `@property` do `Repo`
Em [models/repo.py:8-18](models/repo.py#L8-L18), as properties retornam a si mesmas:
```python
@property
def id(self):
    return self.id   # chama a própria property → recursão infinita
```
O correto seria `return self._id` (e o mesmo para `_name` e `_stars`). Não aparece na execução porque o código só usa o `__str__`, que acessa `self._id` diretamente. Mas `repo.id` causaria `RecursionError`.

### 5.3 Detalhes menores
- O `import json` em [github/client.py:2](github/client.py#L2) (e no `bad_src.py`) não é usado.
- Em [github/client.py:8](github/client.py#L8), um `@classmethod` recebe `self` como primeiro parâmetro. Funciona, mas por convenção deveria se chamar `cls`, como já está no `RepoParser`.
- O `GithubClient` devolve um dicionário `{"status_code", "body"}` com uma mensagem de erro em texto. Funciona para o exercício, mas mistura um pouco "resposta HTTP" com "mensagem para o usuário". Uma alternativa comum é lançar uma exceção e deixar o `main.py` decidir a mensagem.

---

## 6. Resumo final

O `bad_src.py` não está "errado", ele funciona. O problema é que **qualquer mudança**, seja na API, no formato de saída, nos campos ou no fluxo, obriga a mexer na **mesma classe**, com risco de quebrar o que não tinha relação com a mudança. Ele também não pode ser testado em partes.

A refatoração separa o código por **motivo de mudança**:
- **HTTP** fica no `github/`
- **o que é um repositório** fica no `models/`
- **a conversão de dados** fica no `repo/`
- **a coordenação** fica no `main.py`

Cada peça pode ser entendida, testada e alterada isoladamente. Esse é o objetivo do Princípio da Responsabilidade Única.