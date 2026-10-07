set -euo pipefail
export PATH=/usr/local/bin:/usr/bin:/bin
export BAO_ADDR=https://192.168.70.12:8200 BAO_CACERT=/etc/openbao/ca.crt
bao_login() { BAO_TOKEN=$(bao write -field=token auth/approle/login role_id=@/etc/openbao/$1/role_id secret_id=@/etc/openbao/$1/secret_id); export BAO_TOKEN; }
secret() { bao kv get -mount=secret -field="$2" "hm1/platform/ci/$1"; }
bao_logout() { bao token revoke -self >/dev/null 2>&1 || true; unset BAO_TOKEN; }
clone() { git clone -q "${SERVER%%://*}://ci:$3@${SERVER#*://}/$1.git" "$2" && git -C "$2" remote set-url origin "$SERVER/$1.git"; }
