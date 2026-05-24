# wynnBuildGenerator 要件定義

最終更新: 2026-05-23

## 目的

`wynnBuildGenerator` は、ユーザーが指定した条件に合う Wynncraft の装備ビルドを自動生成し、候補をスコア順に提示する機能である。既存の Wynnbuilder と計算結果がずれることを避けるため、アイテムデータ、ビルド集計、スキルポイント、ダメージ計算、表示用ラベルは可能な限り Wynnbuilder 本体のデータと JavaScript ロジックを参照する。

新規に追加する責務は、専用ページ、検索条件 UI、候補探索、結果一覧、既存 Builder へ渡せるビルド出力に限定する。

## 基本方針

- メインサイトは静的サイトのまま維持する。
- FastAPI などの常駐バックエンドは、検索速度やブラウザ制約で必要と判断できるまで追加しない。
- 旧実装 `wynnBuildGenerator_old/` の仕様は参考にするが、計算式やデータ正規化を Python 側に再実装しない。
- 検索候補の評価は Wynnbuilder の `Build`、damage calc、`calculate_skillpoints()` と同じ経路で行う。
- 検索アルゴリズムは高速化してよいが、返却候補の最終評価は既存ロジックで検証する。

## 対象スロット

検索対象は旧実装と同じ 9 装備スロットを基本とする。

- weapon
- helmet
- chestplate
- leggings
- boots
- ring1
- ring2
- bracelet
- necklace

同じリングを `ring1` と `ring2` に採用できる。武器は選択クラスに合うものだけを対象にする。Tome、Powder、Ability Tree、Aspect は初期版では固定または未使用として扱い、後続フェーズで拡張する。

## 入力条件

必須入力:

- class
- level

主な任意入力:

- 固定アイテム
- アイテム tier / restriction / dropRestriction
- 条件式
- スコア式
- 候補数、beam 幅、結果件数などの探索制限
- スキル要求を満たすかの表示・フィルタ有無

条件式は旧実装の考え方を引き継ぎ、`scope`、`key`、`operator`、`value` を持つ。初期スコープは Wynnbuilder の statMap に寄せ、必要に応じて UI 側で「Health」「Walk Speed」などの表示名に変換する。

## 条件式

対応演算子:

- `>=`
- `<=`

複数条件は AND とする。未知の stat key は失敗扱いにせず警告を出す。旧実装の `requirements`、`identifications`、`base`、`derived`、`total` の分離は参考情報とし、実装では Wynnbuilder の `statMap` と表示メタデータに合わせる。

## スキル要求

ここでのスキル要求は、装備に設定されている Strength / Dexterity / Intelligence / Defense / Agility の最小必要値を指す。装備順序、アイテム由来のスキルポイント、セットボーナス、レベルごとの割り振り可能ポイントを含む判定は、Wynnbuilder 既存の `js/skillpoints.js` と `js/builder/build.js` に委譲する。

Generator 側で独自の skill requirement solver は作らない。検索中の軽量 pruning で近似値を使う場合でも、返却候補の最終判定と表示は `Build` が持つ `base_skillpoints`、`total_skillpoints`、`assigned_skillpoints`、`equip_order` を正とする。

## スコアリング

スコアは複数キーの重み付き合算とする。

```json
{
  "maximize": { "hp": 1, "sdRaw": 2 },
  "minimize": { "1stSpellCost": 1 }
}
```

キー名は最終的に Wynnbuilder が使う ID に解決する。UI では検索可能なキーセレクタを用意し、内部 ID と表示名のずれを隠す。

## 検索結果

各結果は次を持つ。

- 各スロットのアイテム
- スコアとスコア内訳
- 条件一致状況
- Wynnbuilder で再表示できる build hash または入力セット
- 主要 stat の概要
- スキル要求の検証結果

結果詳細の完全な数値表示は、可能なら既存 Builder の表示部品または同じ `Build` 評価結果から生成する。

## 表示仕様

ステータスの表示名、数値表記、色、符号、単位、表示順は Wynnbuilder に完全に従う。Generator 独自の stat order、丸め規則、ラベル変換表は原則として作らない。

参照する表示ロジック:

- `js/display.js`
- `js/display_constants.js`
- `displayBuildStats()`
- `displayFixedID()`
- Builder で使われている display command 群

検索結果一覧では省略表示をしてよいが、詳細表示と Builder で開いた結果の表記が食い違ってはいけない。省略表示に使う主要 stat も、内部 ID、表示名、数値フォーマットは Wynnbuilder のものを使う。

## Wynnbuilder 連携

最終的に既存 Wynnbuilder から `wynnBuildGenerator` へ移動できる導線を追加する。導線は sidebar または Builder ページ内の関連アクションとして置き、既存の `Build Search` 外部リンクとは別に、このリポジトリ内の Generator ページへ遷移する。

Generator の検索結果は、既存 Wynnbuilder で閲覧・調整できることを必須要件とする。各結果には次の操作を用意する。

- Builder で開く
- Builder 用 URL / build hash をコピーする
- 検索条件と選択結果を Generator 側で再現できる URL をコピーする

Builder で開く場合は、`js/builder/build_encode_decode.js` の encode/decode 仕様に合わせて、装備、武器、level、必要に応じて powder / tome / atree / aspect を渡す。初期版で未対応の要素は空または Builder 既定値として扱い、結果画面に未反映であることを表示する。

## 非目標

初期版では以下を対象外とする。

- 独立した hosted backend
- データベース永続化
- Python 側での Wynnbuilder 計算式再実装
- Crafted item の完全探索
- Ability Tree / Aspect を含む完全最適化
- ML/DL による hard pruning
