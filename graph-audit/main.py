from auth import get_token, token_scopes
from graph_client import GraphClient


def main():
    token = get_token()
    print("Scopes en el token:", token_scopes(token))

    graph = GraphClient(token)
    data = graph.get(
        "/users",
        params={
            "$top": 5,
            "$select": "id,displayName,userPrincipalName,userType,accountEnabled",
        },
    )
    for u in data["value"]:
        print(f"{u['displayName']} | {u['userPrincipalName']} | {u['userType']} | activo={u['accountEnabled']}")


if __name__ == "__main__":
    main()