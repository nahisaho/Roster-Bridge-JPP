以下は、生成AIが正しく理解し、高品質な出力を生成しやすくするために**構造化・修正したプロンプト**です。目的・仕様・前提条件・要件・テストといった分類に整理し、曖昧さや重複を排除しています。

---

## 🔧 プロンプト（構造化・修正済）

---

### 🎯 ゴール（目的）

以下の機能を持つ**Roster APIサービス**を、**Python / FastAPI**で開発する。

* ユーザーが**OneRoster Japan Profile形式のCSVファイル**をAPI経由でアップロード可能にする
* アップロードされたデータをSQL DBに保存
* 保存されたデータに対して、以下2種類の**OneRoster Rest APIエンドポイント**を提供する

  * **全件取得API**
  * **差分取得API**（`FirstSeenDateTime`, `LastSeenDateTime` を使用）

---

### 📂 入力データ

* **CSVスキーマファイル名**: `oneroster_japan_profile_complete_schema_recreated.json`
* **CSVファイルの構造**: OneRoster Japan Profile 完全準拠
* **各レコードの主キー**: `sourcedId`

---

### 🛠️ 使用技術

* **開発言語**: Python（仮想環境を構築）
* **フレームワーク**: FastAPI
* **デプロイ方法**: Docker（Linuxベースイメージ）
* **DB選択肢**:

  * SQLite（テスト用）
  * Azure Database for PostgreSQL
  * Azure Database for MySQL
  * Azure Database for MariaDB
  * Azure Database for Microsoft SQL

---

### 🔐 セキュリティ要件

* APIの**ファイルアップロード**および**データ取得（全件・差分）**は**認証キー**を利用して制限

---

### 💾 データ取扱仕様

* CSVアップロード時にその**アップロード日**を取得
* 各レコードに以下の2つのタイムスタンプを保存:

  * `FirstSeenDateTime`: 初回アップロード日時
  * `LastSeenDateTime`: 最終更新日時
* 同じ `sourcedId` のレコードが既に存在する場合は、

  * `FirstSeenDateTime` は変更しない
  * `LastSeenDateTime` のみ更新

---

### 🧪 テスト要件

* **単体テスト・統合テスト**はSQLiteを使用
* 各APIエンドポイントに対する正常系・異常系テストを実施

---

### 📝 ログ要件

* 実行時ログはすべて **syslog** に保存

