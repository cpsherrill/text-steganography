# Project Design: A Modular Python Library for Lossless Text Steganography and Fingerprinting

**Status:** Initial design and project-definition document  
**Working project name:** Text Steganography  
**Package name:** To be chosen, but the public name should use the word **steganography** so that the purpose is recognizable and searchable  
**Primary implementation language:** Python

---

## 1. Executive summary

The project is a general-purpose Python library for embedding small hidden payloads into text by changing the text’s literal representation without intentionally changing what a human reader understands. The library should support multiple deterministic, lossless or effectively lossless text-steganography techniques, let the user choose which techniques to enable, estimate exactly how much information a particular piece of text can carry, encode a payload, recover it later, and diagnose what survived when a carrier or transport altered the text.

A central use case is **recipient fingerprinting**. Suppose the same document is distributed to 1,000 recipients. Each recipient receives a visually equivalent but literally distinct version containing a different hidden identifier. If one version later appears elsewhere, the library should be able to decode the identifier. If only part of the document survives, or if some of the steganographic distinctions have been normalized away, the library should still be able to determine which of the 1,000 candidate versions remain possible and rank the likely sources.

The project is not intended to rely on probabilistic word choice, stylometry, paraphrasing, frequency analysis, or model-specific statistical watermarks. The user specifically wants deterministic techniques in which the hidden information resides in concrete representational choices: one apostrophe code point rather than another, one Unicode space rather than another, a zero-width character at an eligible location, one canonical-equivalent Unicode sequence rather than another, a line-ending choice, a markup-equivalent representation, or another explicitly selected textual variant.

The core design principle is separation of concerns:

1. The **payload** is arbitrary hidden data, normally exposed as bytes.
2. A **payload framing layer** records length, version, integrity information, and related metadata.
3. An optional **error-correction layer** adds redundancy.
4. A **symbol-packing layer** maps the resulting bitstream or codeword into the capacities offered by the text.
5. Independent **steganographic channels** discover eligible locations and provide the literal variants available at each location.
6. A versioned **codec configuration** defines the channel set, channel order, repertoire constraints, packing strategy, error-correction choice, and other decisions needed by both encoding and decoding.
7. **Carrier and transport profiles** provide simple recommendations about which channels are likely to survive in a particular environment, while leaving the final configuration under the user’s control.
8. A separate **identification layer** compares a complete or partial observation against a known set of candidate payloads or generated variants.

Capacity analysis, diagnostics, uncertainty, and partial recovery should be first-class features rather than afterthoughts.

---

## 2. The core idea

The user begins with ordinary, unencoded text, referred to in this document as the **cover text**. The user also supplies:

- a small payload to hide;
- a codec configuration describing the enabled steganographic channels and their options;
- optionally, an error-correction configuration;
- optionally, a carrier/transport profile used for warnings and recommendations.

The encoder produces **stegotext**: text that should appear equivalent to the intended reader but whose exact sequence of characters or textual representations contains the payload.

The decoder receives the stegotext and the same codec definition. In the ordinary full-text case, the decoder should not require separate placement metadata. Each channel should deterministically rediscover its relevant sites, classify the literal variant at each site, reconstruct the encoded symbol sequence, reverse error correction and framing, and return the recovered payload.

The simplest conceptual pipeline is:

```text
cover text
    + payload
    + codec configuration
        |
        v
capacity analysis
        |
        v
payload framing
        |
        v
optional error-correction encoding
        |
        v
bit/symbol packing
        |
        v
channel-specific substitutions or insertions
        |
        v
stegotext
```

Decoding reverses this pipeline:

```text
stegotext
    + same codec configuration
        |
        v
channel observations
        |
        v
known / unknown / ambiguous symbol sequence
        |
        v
optional error-correction decoding
        |
        v
payload frame validation
        |
        v
recovered payload and diagnostics
```

The project should explicitly distinguish **encoding** from **encryption**. Steganography hides the existence or provenance marker of a payload; it does not inherently make that payload confidential. A recipient number such as `847`, an opaque token, a UUID, or a cryptographic digest can be embedded, but the steganographic layer itself should not be described as encryption or decryption. Encryption, signing, message authentication, or tokenization can be layered around the payload if desired.

---

## 3. Terminology

A clear vocabulary is important because several words are easily overloaded.

### 3.1 Steganography

**Steganography** is the broad practice of hiding information within another apparently ordinary carrier. In this project, the carrier is text or a text-bearing format.

### 3.2 Text watermarking

**Text watermarking** is a useful broad description for placing a detectable marker in text. Some watermarking systems are probabilistic, linguistic, or statistical. This project focuses only on deterministic representational techniques.

### 3.3 Fingerprinting

**Fingerprinting** means giving different recipients distinct marked copies. The hidden payload identifies the copy or recipient. The 1,000-recipient example is a fingerprinting application.

### 3.4 Traitor tracing

**Traitor tracing** is the process of using fingerprints to identify the source of a disclosed copy. In strict technical usage, traitor tracing can also involve adversarial behavior and collusion among multiple recipients. The initial project supports straightforward source identification and candidate narrowing. It should not claim collusion resistance unless a later design explicitly adds fingerprint codes intended for that threat model.

### 3.5 Cover text and stegotext

- **Cover text:** the ordinary, unencoded source text.
- **Stegotext:** the encoded output containing hidden information.

### 3.6 Payload

The **payload** is the hidden information. The lowest-level public representation should be bytes, with convenience adapters for integers, strings, UUIDs, hashes, or structured data.

The decoder should return the recovered payload, not merely a hash of it. A caller may choose to embed a hash or opaque identifier, but that interpretation belongs above the steganography layer.

### 3.7 Channel

A **channel** is one steganographic mechanism: punctuation variants, cross-script homoglyphs, zero-width characters, Unicode-space variants, line endings, canonical-equivalent Unicode sequences, markup-equivalent representations, and so forth.

A channel is responsible for finding its own eligible locations, describing the variants available at each location, applying a selected variant, and observing a selected variant during decoding.

### 3.8 Embedding site

An **embedding site** is a location in the cover text at which a channel can make a representational choice. An apostrophe occurrence may be one site. A boundary between two words may be another. A line break may be another.

### 3.9 Variant and symbol

A **variant** is one literal representation available at an embedding site.

A **symbol** is the abstract choice represented by a variant. If a site permits four variants, those variants can represent symbol values `0`, `1`, `2`, and `3`. In the simple power-of-two case, that site can encode two bits.

The term **symbol alphabet** or **variant alphabet** may be used for the set of choices at one site. This should not be confused with a natural-language alphabet or Unicode script.

### 3.10 Script and character repertoire

The user initially referred to an alphabet, such as the Latin alphabet. For the library, the more precise terms are:

- **Script:** Latin, Greek, Cyrillic, Arabic, and so on.
- **Character repertoire:** the exact set of code points that a configuration permits.

A cross-script homoglyph channel might use Latin, Greek, and Cyrillic look-alikes. A conservative policy might permit Latin punctuation variants but prohibit all cross-script substitutions.

### 3.11 Carrier

A **carrier** is the representation or format that holds the stegotext at a particular stage. Examples include:

- a Unicode string;
- a plain-text file;
- a Markdown document;
- an HTML document;
- a source-code file;
- a plain-text email body;
- an HTML email body;
- a DOCX document;
- a Google document;
- a PDF;
- a social-media post;
- a chat message.

The carrier describes what the content *is*.

### 3.12 Transport

A **transport** is the path, application, or transformation through which the carrier passes. Examples include:

- an email composer, server, and receiving client;
- a social-media composer and API;
- copying through the clipboard;
- a browser and DOM serializer;
- Git;
- an IDE;
- a code formatter;
- a Markdown renderer;
- an HTML sanitizer or minifier;
- Word-to-Google-Docs import and export;
- PDF generation and text extraction;
- SMS gateways;
- an OCR process;
- an LLM rewrite or summarization step.

The transport describes what *happens to* the carrier. The same carrier can survive one transport and fail in another.

### 3.13 Codec configuration

The **codec configuration** is the complete, versioned definition required to interpret the watermark. It includes the channels, their order, their parameters, repertoire constraints, packing method, framing method, error-correction method, and any deterministic selection rules.

Both encoder and decoder require the same effective codec definition.

### 3.14 Error, erasure, insertion, and deletion

Text transports can damage an encoded signal in several ways:

- **Substitution/error:** one valid variant becomes another valid or invalid variant.
- **Erasure:** a site remains identifiable, but its encoded choice is lost or normalized to a neutral form.
- **Insertion:** new text or new eligible sites appear.
- **Deletion:** text or sites disappear.
- **Reordering:** sections move.
- **Synchronization loss:** the decoder can no longer tell which observed symbol corresponds to which codeword position.

The library should retain these distinctions because ordinary Hamming-style bit-error correction does not solve every failure mode.

---

## 4. Goals

The project should pursue the following goals.

### 4.1 Deterministic, representational hiding

Encoding should be deterministic for a fixed cover text, payload, configuration, and optional seed or key. Hidden information should reside in literal textual choices rather than in statistical tendencies.

### 4.2 Lossless or invariant-preserving behavior

The watermark must not intentionally alter the intended content. Because changing characters necessarily changes the byte sequence, “lossless” must be defined in terms of an invariant rather than byte identity.

Different channels may preserve different invariants:

- **Canonical-text invariant:** canonicalizing the stegotext reproduces the cover text.
- **Rendered-text invariant:** the target renderer displays the same visible text.
- **Semantic invariant:** the meaning or program behavior remains the same.
- **Structural invariant:** the document structure remains equivalent under a defined parser.

The library should document which invariant each channel claims and should avoid pretending that every technique is identical under every font, renderer, parser, accessibility tool, or locale.

### 4.3 User-selected, composable channels

The user chooses which channels to enable. Profiles may recommend a configuration, but recommendations are advisory. The library should warn about unsafe or fragile choices while allowing explicit override.

### 4.4 First-class capacity estimation

Before encoding, the user should be able to ask how much information a given text can carry under a given configuration. The report should separate theoretical capacity, realizable packed capacity, protocol overhead, error-correction overhead, and usable payload capacity.

### 4.5 Payload/channel separation

Any channel should be able to carry the same payload representation. Payload handling, framing, error correction, and symbol packing should not be entangled with apostrophe handling, whitespace handling, or another specific channel.

### 4.6 Diagnostics and transparency

Encoding and decoding should report:

- sites found;
- capacity by channel;
- sites used;
- warnings;
- observed symbols;
- unknown or ambiguous symbols;
- errors corrected;
- erasures encountered;
- integrity-check status;
- surviving capacity by channel;
- candidate matches when identification is requested.

### 4.7 Graceful partial recovery

When complete decoding is impossible, the library should expose partial observations rather than returning only failure. The caller should be able to determine which candidate payloads remain consistent with the surviving evidence.

### 4.8 Extensibility

New channels, repertoires, packing methods, error-correction adapters, carrier adapters, and transport profiles should be addable without modifying the entire core.

### 4.9 Stable, reproducible decoding

A copy encoded by one released version should remain decodable later. Channel mappings and configuration schemas therefore need stable identifiers and versions.

---

## 5. Non-goals

The initial project should explicitly exclude or defer the following.

### 5.1 Linguistic and stylometric watermarking

The project will not initially alter:

- word choice;
- sentence structure;
- use of contractions;
- punctuation frequency as a statistical signal;
- “it is” versus “it’s” patterns;
- stylistic tendencies;
- paraphrases;
- model token probabilities;
- LLM generation distributions.

These methods are not sufficiently deterministic or strictly lossless for the intended design.

### 5.2 Statistical LLM watermarks

Token-distribution watermarks and detectors for generated text are a separate field and are not part of the core library.

### 5.3 Guaranteed survival through arbitrary rewriting

No literal-character watermark can be expected to survive arbitrary retyping, OCR, semantic paraphrasing, translation, or aggressive normalization. The library should state its assumptions and measure survival rather than promise universality.

### 5.4 Cryptographic confidentiality

Steganography does not replace encryption. Confidentiality and authentication may be optional payload transforms, but they are not the same problem.

### 5.5 Automatic platform integrations in the core

The core should operate on text or carrier-adapter abstractions. It does not need to send email, post to X/Twitter, edit Google Docs, or commit to Git. Platform integrations can be separate extras or test harnesses.

### 5.6 Binary-file metadata as the main technique

File metadata, custom document properties, PDF metadata, ZIP extra fields, and similar container tricks may be useful but are outside the central “hidden in the literal text” concept. They can be documented separately rather than conflated with text steganography.

---

## 6. Information capacity and entropy

The user’s entropy-based intuition is the right foundation.

### 6.1 A site with four variants

Suppose an eligible apostrophe site can safely use exactly four distinguishable variants. The site has four possible states:

```text
0, 1, 2, 3
```

Four states can carry:

```text
log2(4) = 2 bits
```

A site with two variants carries one bit. A site with eight variants carries three bits.

The important caveat is that a hypothetical list of four apostrophe-like characters is not automatically a safe four-symbol alphabet. Some characters have directional, semantic, typographic, linguistic, search, or normalization differences. The channel must decide which variants are valid at that particular location and under the selected repertoire policy.

### 6.2 Non-power-of-two sites

A site may have three, five, or six variants. Its theoretical information capacity is `log2(m)` bits, where `m` is the number of choices, but a simple fixed-bit mapping cannot use a fractional number of bits.

The core should support or at least leave room for two packing modes:

1. **Power-of-two packing:** use only the largest power-of-two subset of variants. A three-variant site carries one bit and leaves one variant unused. This is simple and easy to reason about.
2. **Mixed-radix or enumerative packing:** combine several sites with different radices and use all or nearly all available combinations. This is denser but more complex.

The channel should report available symbols rather than deciding how bits are packed. The packing layer can then choose the strategy.

### 6.3 Capacity across many sites

If site `i` has `m_i` variants, the number of distinct representational combinations is:

```text
M = product(m_i)
```

The theoretical total capacity is:

```text
log2(M) = sum(log2(m_i))
```

The maximum fixed-length binary payload that can be represented by all combinations is approximately:

```text
floor(log2(M))
```

Actual usable payload capacity is smaller because of:

- frame headers;
- payload length;
- codec/version identifiers;
- checksums or message-authentication tags;
- error-correction redundancy;
- synchronization markers;
- interleaving or repeated blocks;
- unused combinations in a simple packing scheme.

### 6.4 The 1,000-recipient example

To assign a distinct raw identifier to 1,000 recipients requires at least:

```text
ceil(log2(1000)) = 10 bits
```

Ten raw bits are not necessarily enough for a robust fingerprint. If the design adds framing, integrity checks, and error correction, the text may need substantially more than ten bits of gross capacity.

A useful capacity report should therefore say something like:

```text
Raw theoretical capacity:          42.7 bits
Realizable packed capacity:        42 bits
Frame and integrity overhead:      12 bits
Error-correction overhead:         14 bits
Usable payload capacity:           16 bits
Distinct payload values possible:  65,536
```

### 6.5 Capacity must be content-dependent

Capacity depends on both the text and the configuration. A punctuation channel has no capacity in text with no eligible punctuation. A line-ending channel has no capacity in a single-line string. A homoglyph channel has different capacity depending on the letters present and the repertoire restrictions.

This makes `analyze(text, config)` a core API rather than a documentation-only estimate.

---

## 7. Steganographic channel taxonomy

The library should organize techniques into explicit channel families. Each individual channel should document its invariants, capacity model, supported repertoires, common transformations, and risks.

### 7.1 Punctuation variants

This family selects among visually or typographically similar punctuation characters.

Possible categories include:

- straight versus typographic apostrophes;
- left and right single quotation marks where grammatically appropriate;
- straight versus typographic double quotation marks;
- hyphen, nonbreaking hyphen, en dash, em dash, minus sign, or other dash-like forms where the selected semantics permit;
- three periods versus a single ellipsis character;
- colon-, semicolon-, prime-, or quote-like variants in carefully constrained contexts.

This channel can be relatively understandable to users, but it is not automatically safe. Curly quotes may be normalized to straight quotes, directionality may matter, line breaking can change, and some variants are not true semantic substitutes.

The implementation should be context-sensitive. For example, an opening quotation mark and an apostrophe inside a contraction should not blindly share the same variant table.

### 7.2 Same-rendering Unicode sequence variants

Some visible characters can be represented as either:

- a precomposed code point; or
- a base character followed by one or more combining marks.

For example, a visibly accented character may have canonically equivalent NFC and NFD forms.

This channel is attractive because the rendered character can be extremely similar or identical, but it is highly fragile under Unicode normalization. It is useful precisely when the transport is known not to normalize, and it is an excellent example of why carrier/transport guidance matters.

The channel should distinguish:

- canonical equivalence;
- compatibility equivalence;
- merely similar rendering.

Compatibility normalization can alter meaning more aggressively and should not be treated as interchangeable with canonical equivalence.

### 7.3 Homoglyph and confusable-character substitutions

A homoglyph channel substitutes characters that look alike or nearly alike. The user’s example was a Latin `O` versus a Greek omicron, and Cyrillic offers another visually similar character.

Possible substitutions may occur:

- within one script;
- across Latin, Greek, Cyrillic, or other scripts;
- among mathematical alphanumeric forms;
- among letter-like symbols and ordinary letters;
- among digit/letter confusables.

Cross-script homoglyphs can provide substantial capacity but are one of the riskiest channels. They may:

- trigger phishing or security detectors;
- break search and indexing;
- alter identifiers in source code;
- render differently in another font;
- confuse screen readers;
- be normalized or rejected;
- create visually deceptive text.

Cross-script substitutions should be behind explicit opt-in and disabled in conservative profiles. The configuration should support policies such as:

```text
same-script only
Latin-only
no identifier characters
punctuation-only
explicit allowlist of code points
```

### 7.4 Invisible Unicode format characters

This family encodes information by inserting or selecting invisible or nearly invisible characters, including categories such as:

- zero-width spaces;
- zero-width joiners;
- zero-width non-joiners;
- word joiners;
- zero-width no-break behavior;
- variation selectors;
- directional marks or other format controls.

These characters are often described together, but they do not have equivalent semantics. Joiners and non-joiners can materially affect shaping in some scripts. Directional controls can affect display order. Variation selectors can affect emoji or glyph presentation. Some invisible characters are stripped by editors, sanitizers, messaging platforms, or normalization steps.

The channel catalog should therefore be granular. A user should not merely enable “all zero-width characters.” Each subchannel should declare where insertion is allowed and what it may alter.

### 7.5 Whitespace-character variants

A boundary that visually appears to contain a space may be represented by different Unicode whitespace characters, such as:

- ordinary ASCII space;
- nonbreaking space;
- narrow no-break space;
- thin or hair spaces;
- other Unicode space separators.

A whitespace channel can also use tabs versus spaces where the carrier preserves both.

Risks include:

- changed line wrapping;
- changed justification;
- changed tokenization;
- trimming;
- collapsing;
- HTML whitespace rules;
- syntax changes in code;
- normalization by editors;
- copy/paste loss.

The channel should separate “visually similar space characters” from “structural whitespace patterns,” because they have different semantics and transports.

### 7.6 Structural whitespace

Structural whitespace techniques include:

- one versus multiple spaces where collapsing is guaranteed;
- tabs versus spaces;
- indentation patterns;
- trailing whitespace;
- blank-line choices;
- placement of optional line breaks;
- line wrapping at equivalent boundaries.

These can be high-capacity in source-like carriers but are frequently destroyed by formatters, linters, editors, HTML rendering, or automatic trimming.

Structural whitespace should normally require a carrier-aware parser or profile. It is unsafe to apply a generic whitespace channel to Python source, YAML, Makefiles, or any language in which whitespace is syntactic.

### 7.7 Line-ending variants

Text files may use:

- LF;
- CRLF;
- in some environments, CR.

Line endings can encode choices at each line break, but transports often normalize them globally. Git settings, editors, file upload systems, email processing, and operating-system conversions commonly destroy this signal.

This channel is straightforward and deterministic, but it is best treated as a file-transport channel rather than a general visible-text channel.

### 7.8 Escape and entity representations

Some carriers permit the same logical character to be represented in several source-level ways:

- a literal Unicode character;
- an HTML named entity;
- an HTML decimal numeric reference;
- an HTML hexadecimal numeric reference;
- a JSON or source-code Unicode escape;
- a source-code hexadecimal or octal escape where the language permits;
- a URL literal character versus percent-encoding in an appropriate component.

These channels preserve parsed content rather than literal source appearance. They require a carrier parser and must not be applied as generic string substitutions.

### 7.9 Markup-equivalent representations

HTML, Markdown, XML, and similar carriers can contain multiple syntactic forms that render or parse equivalently.

Examples may include:

- literal characters versus entities;
- optional syntactic whitespace;
- quoting choices around attributes;
- attribute order where the format and application treat it as irrelevant;
- equivalent emphasis or link syntax in Markdown;
- optional tags or escapes in narrowly defined contexts;
- alternate but equivalent serialization of an AST.

These channels should operate on a parsed representation, not by regular-expression substitution. HTML sanitizers, minifiers, Markdown renderers, and content-management systems may canonicalize them.

### 7.10 Source-code lexical and syntactic equivalences

Source code offers carrier-specific possibilities such as:

- quote style where string contents and language rules permit;
- equivalent escape sequences;
- numeric literal spellings;
- optional parentheses;
- comment placement;
- whitespace where nonsyntactic;
- equivalent import or declaration formatting;
- line endings.

This is a distinct family because the preserved invariant is program behavior or parsed AST, not necessarily visible prose. Every supported programming language would need its own parser-aware adapter and safety rules. Generic text channels must not silently modify identifiers or syntactically meaningful whitespace.

### 7.11 Rich-document representations

Word documents, Google Docs, RTF, and related formats can preserve visible text while representing it through different internal runs, XML structures, style references, or Unicode choices.

These are possible future carrier backends, but they are more than simple string channels. The implementation should likely separate:

- text-level channels inside document runs;
- document-structure channels;
- metadata channels, which are outside the central text focus.

Google Docs is also a moving service rather than a static file format, so import, export, copy/paste, and API editing should be treated as transports.

### 7.12 PDF representations

PDF is a carrier in the broad sense, but it is especially difficult. Visually identical PDF text can have radically different underlying encodings, font mappings, object structures, and extraction behavior. A text-level watermark embedded before PDF generation may survive visual rendering while disappearing during text extraction, or vice versa.

PDF support should probably begin as documentation and test profiles rather than an early general-purpose encoder. A future PDF adapter would need a narrowly stated invariant and threat model.

### 7.13 Formatting or style channels

A rich document can hide data in font, kerning, color, style-run boundaries, or other formatting details. These are genuine document steganography techniques, but they do not fit the user’s original emphasis on literal character differences. They should be treated as an optional later family, not silently mixed into the text-channel core.

---

## 8. Carrier catalog

The documentation should discuss at least the following carriers.

### 8.1 Plain and structured text

- in-memory Unicode strings;
- `.txt` files;
- Markdown;
- reStructuredText;
- HTML;
- XML;
- JSON;
- YAML;
- CSV and TSV;
- source-code files;
- configuration files;
- code comments and documentation strings;
- wiki or CMS source text.

### 8.2 Communication text

- plain-text email;
- HTML email;
- SMS;
- MMS captions;
- chat and messaging applications;
- social-media posts, including X/Twitter-like short posts;
- forum posts;
- issue trackers;
- pull-request descriptions and comments;
- collaborative document comments.

### 8.3 Rich and rendered documents

- Microsoft Word / DOCX;
- Google Docs;
- RTF;
- OpenDocument Text;
- PDF;
- EPUB and other ebook formats;
- slide text;
- spreadsheet cell text.

### 8.4 Software and development carriers

- raw source code;
- Git blobs and diffs;
- notebooks;
- generated documentation;
- code review comments;
- commit messages;
- package metadata.

The core library does not need to implement every carrier immediately. The list is useful because the profile and compatibility system should not assume that “text” is one homogeneous environment.

---

## 9. Transport catalog

The same encoded text can behave differently depending on the path it takes. Useful transports and transformations to model include:

- saving and reopening in common text editors;
- copying and pasting through the operating-system clipboard;
- browser input fields and content-editable elements;
- browser DOM parsing and serialization;
- email composition, MIME encoding, server transit, and client display;
- social-media web composers and mobile applications;
- platform APIs;
- SMS gateways;
- chat applications;
- Git checkout and commit behavior;
- `.gitattributes` and line-ending conversion;
- IDE save hooks;
- code formatters and linters;
- Markdown rendering and reserialization;
- HTML sanitizers and minifiers;
- CMS rich-text editors;
- Word import/export;
- Google Docs import/export and copy/paste;
- PDF generation;
- PDF text extraction;
- Unicode NFC, NFD, NFKC, or NFKD normalization;
- character-encoding conversion;
- spellcheck or smart-quote replacement;
- search-index ingestion;
- OCR;
- retyping;
- LLM rewriting, summarization, or translation.

A **transport chain** may contain several of these. For example:

```text
Markdown file
  -> Git
  -> static-site generator
  -> HTML minifier
  -> browser DOM
  -> clipboard
  -> email composer
```

A single flat “safe for Markdown” label cannot fully describe that chain. The project should nevertheless keep the user-facing recommendations simple and explain the underlying transformations when needed.

---

## 10. Carrier and transport profiles

Profiles provide advisory defaults, not restrictions.

A profile might be named for a combination such as:

```text
plain_text_conservative
markdown_git
html_browser
html_email
social_post
source_code_python
docx_word_roundtrip
google_docs_copy_paste
pdf_generated_then_extracted
```

Each profile can specify:

- recommended channels;
- conditionally safe channels;
- fragile channels;
- channels known to be stripped;
- repertoire restrictions;
- expected normalization;
- expected whitespace behavior;
- expected error model;
- evidence or test date;
- warnings;
- suggested error-correction level.

A simple documentation matrix could use labels such as:

- **Recommended**
- **Conditional**
- **Fragile**
- **Unsupported**
- **Unknown / untested**

The configuration remains explicit and user-controlled. A profile may generate warnings, but the caller can opt into a fragile technique.

The distinction among three layers should remain clear:

1. **Capabilities:** what the software can technically encode.
2. **Recommendations:** what is likely to survive a stated carrier/transport.
3. **Configuration:** what the user actually chooses.

---

## 11. Codec configuration

The codec configuration is central because the encoder and decoder must agree about where the entropy lives and how to interpret it.

A configuration should include at least:

```text
schema version
channel list
channel order
channel-specific options
script/repertoire constraints
site-selection rules
channel-conflict policy
packing method
payload framing format
integrity method
error-correction method and parameters
interleaving or redundancy settings
synchronization strategy
optional deterministic seed or key
optional profile reference
```

### 11.1 Versioning

Every channel and mapping should have a stable identifier and version. A configuration should be serializable to JSON or another portable form and should have a canonical digest, such as a `codec_id`.

The digest can be stored externally with the recipient database. An optional embedded codec identifier may be useful, but it consumes capacity and does not remove the need to know which channel family to use to find it. External configuration should therefore remain the basic model.

### 11.2 Channel order

The order of channels and sites must be deterministic. Two implementations using the same configuration must enumerate sites in the same order.

A possible stable ordering is:

1. configuration channel order;
2. canonical text position;
3. channel-defined subsite order;
4. stable tie-breaker.

### 11.3 Conflict handling

Two channels may attempt to modify the same span. For example, a punctuation homoglyph channel and a general Unicode-normalization channel may both claim one character.

The planner should detect overlaps and either:

- reserve the site for the first channel;
- choose according to explicit priority;
- reject the configuration;
- allow a declared composition rule.

Silent conflicts would make capacity estimates and decoding unreliable.

### 11.4 Conservative defaults

A default profile should be conservative. Cross-script homoglyphs, bidirectional controls, semantically active joiners, and other risky characters should require explicit opt-in.

---

## 12. Channel interface

A channel should be an independent plugin-like component.

A conceptual interface might include:

```python
class Channel(Protocol):
    id: str
    version: str

    def discover_sites(
        self,
        canonical_text: str,
        context: ChannelContext,
    ) -> Sequence[EmbeddingSite]:
        ...

    def apply_symbol(
        self,
        text: str,
        site: EmbeddingSite,
        symbol: int,
    ) -> str:
        ...

    def observe(
        self,
        text: str,
        context: ChannelContext,
    ) -> Sequence[Observation]:
        ...

    def compatibility(self) -> ChannelMetadata:
        ...
```

An `EmbeddingSite` may contain:

```text
channel identifier and version
stable site identifier
text span or insertion boundary
local anchor
canonical representation
available variants
radix / number of symbols
claimed invariant
risk metadata
fragment-decoding capability
```

An `Observation` may contain:

```text
site identifier, when recoverable
observed symbol, if known
state: known / erased / ambiguous / invalid
possible symbols
local anchor
confidence or reliability metadata
raw observed code points
```

The exact interface can change, but the important design rule is that the channel reports **symbols and observations**, while the core manages payload bits, packing, framing, error correction, and candidate identification.

---

## 13. Deterministic site discovery

The earlier design assumes that no separate placement manifest is required for ordinary decoding. That is possible only if channels deterministically rediscover their sites from the encoded text.

A useful approach is:

1. Each channel defines a canonical representation for all of its variants.
2. The decoder canonicalizes enough information to recognize that several literal forms belong to one channel site.
3. Sites are enumerated in a stable order.
4. The current literal form maps back to a symbol.

For example, if four apostrophe variants all canonicalize to one abstract apostrophe site, the channel can detect the occurrence and map the actual code point to `0` through `3`.

This requirement should be tested rigorously. A channel that cannot rediscover sites without the original cover text must declare that limitation.

---

## 14. Payload representation and framing

### 14.1 Public payload type

The core public payload should be bytes. Convenience helpers can support:

- integer recipient IDs;
- UTF-8 strings;
- UUIDs;
- fixed-width tokens;
- hashes;
- application-specific records.

For a recipient ID, the application may choose to embed an opaque random token rather than personally identifying information. The caller then resolves the token in a database.

### 14.2 Internal bitstream

The framed and error-corrected payload will normally become a bitstream or a sequence of code symbols before being packed into text sites.

### 14.3 Frame contents

A frame may include:

- magic or format marker;
- frame version;
- payload length;
- payload type identifier, if convenience codecs need it;
- optional codec/configuration digest;
- payload bytes;
- checksum or CRC;
- optional cryptographic authentication tag.

Not every field must be present in a minimal configuration. The capacity report must show their cost.

### 14.4 Integrity versus correction

A checksum answers, “Did we recover the intended frame?” Error correction attempts to repair damage. Both are useful. A decoder should not silently return bytes as a successful payload when the integrity check fails.

### 14.5 Authentication and secrecy

A MAC can help distinguish a genuine watermark from random compatible symbols if the caller has a secret key. Encryption can hide the recipient token from someone who discovers the channel. These should be optional payload transforms and clearly separated from text embedding.

---

## 15. Symbol packing

The symbol-packing layer maps the framed codeword into sites of different radices.

### 15.1 Simple binary mode

The first implementation may choose only binary sites or power-of-two subsets. This keeps mapping straightforward and makes error models easier to understand.

### 15.2 Fixed-width power-of-two mode

A site with four variants carries two bits; a site with eight variants carries three. A site with three variants may use only two choices.

### 15.3 Mixed-radix mode

A later or advanced implementation can treat the sequence of radices as a mixed-radix number system and map a payload integer into the full Cartesian product of site choices.

This recovers capacity otherwise lost at non-power-of-two sites, but it introduces design questions:

- how to stream rather than materialize a huge integer;
- how errors propagate through the packed representation;
- how to support partial observations;
- how to combine with binary error-correcting codes;
- how to remain stable across site changes.

The interface should permit mixed-radix support even if the initial implementation is conservative.

### 15.4 Interleaving

Error-corrected bits should optionally be interleaved across:

- text positions;
- channels;
- paragraphs or blocks.

Interleaving prevents one normalized paragraph or one stripped channel from destroying a contiguous codeword segment.

---

## 16. Error correction

The user wants error correction to be built into the design but would prefer not to implement mature coding theory from scratch.

### 16.1 Generic error-correction layer

The steganography core should define a small protocol for error-correction adapters. The core should not hard-code Hamming, Reed–Solomon, BCH, or another family into channel implementations.

A conceptual interface is:

```python
class ErrorCorrectingCodec(Protocol):
    id: str
    version: str

    def encode(self, payload_bits: BitSequence) -> BitSequence:
        ...

    def decode(
        self,
        observations: BitObservations,
    ) -> ErrorCorrectionResult:
        ...

    def capacity_cost(self, payload_bits: int) -> ErrorCorrectionCost:
        ...
```

### 16.2 Prefer an existing implementation

The implementation plan should be:

1. Survey established Python packages and native libraries for suitable codecs.
2. Wrap them behind the project’s adapter interface.
3. Avoid reimplementing coding algorithms unless necessary.
4. If the project discovers that a genuinely generic, reusable error-correction abstraction is missing, consider a separate repository/package rather than embedding a large unrelated subsystem inside the steganography library.

A thin adapter protocol can remain in the main package even when implementations come from dependencies.

### 16.3 Hamming-code intuition

The user is familiar with Hamming codes as a system that adds redundancy so a small number of bit errors can be corrected. That intuition is correct, but standard Hamming codes typically correct a limited number of bit flips in fixed-size codewords. The user-facing configuration should expose concrete code parameters or a named strength profile rather than a vague “correction factor.”

### 16.4 Other codec families

Potential adapters may include:

- no error correction;
- repetition codes;
- Hamming-family codes;
- BCH codes;
- Reed–Solomon codes;
- erasure-oriented codes;
- deletion/insertion-aware codes in a later phase.

The list is illustrative, not a commitment to implement each algorithm.

### 16.5 Errors versus erasures

Text channels often fail by erasure rather than by a clean bit flip. A platform may convert every fancy apostrophe to one neutral apostrophe. If the site remains identifiable, the decoder knows that a symbol was present but lost. An erasure-aware decoder can use that information more effectively than a decoder that treats it as an arbitrary wrong bit.

### 16.6 Synchronization failures

If text is deleted or only an excerpt survives, the positions of later bits may shift. Ordinary Hamming or Reed–Solomon use does not automatically solve this. Fragment handling requires an additional alignment or synchronization design, discussed below.

### 16.7 Capacity reporting

The `analyze` result must include:

- encoded codeword length;
- parity/redundancy overhead;
- stated correction capability;
- erasure capability, if applicable;
- assumptions about fixed positions;
- net payload capacity.

---

## 17. Decoding results

`decode` should return a structured result, not only bytes or an exception.

A possible result model is:

```text
status:
    success
    partial
    ambiguous
    invalid
    insufficient_evidence
payload:
    bytes or None
frame_version
codec_id
integrity_valid:
    true / false / unknown
corrected_errors
erasures
ambiguous_symbols
invalid_symbols
observed_capacity
channel_statistics
partial_observation
warnings
```

When decoding succeeds, the payload is returned. When it does not, the observation should still be usable by the candidate-identification system.

---

## 18. Partial observations and candidate identification

This is a separate feature from error correction and should be designed explicitly.

### 18.1 The basic problem

There may be 1,000 known payloads, one per distributed copy. A leaked copy may have:

- some characters normalized;
- one channel stripped entirely;
- sections removed;
- only one paragraph preserved;
- formatting changed;
- a few variants substituted.

A full payload decode may be impossible. The goal is then to answer:

```text
Which of the 1,000 candidates are still consistent with the surviving evidence?
```

### 18.2 Observation with unknown positions

For a full-length text in which some sites were normalized, the decoder can produce a sequence such as:

```text
1 0 ? 1 ? ? 0 1 1 0 ...
```

The `?` values are erasures or unknown symbols. Candidate payloads can be framed and error-correction encoded into expected codewords and compared with the known positions.

A candidate is:

- **consistent** if it contradicts no known observation;
- **inconsistent** if it differs at one or more reliable observed positions;
- **ranked** by weighted distance if some contradictions are tolerated.

### 18.3 Candidate-identification API

A separate API might be:

```python
identify(
    observed_text,
    candidates,
    config,
    *,
    cover_text=None,
    candidate_texts=None,
) -> IdentificationResult
```

Candidates may be:

- payload bytes;
- recipient IDs converted through a payload codec;
- expected codewords;
- complete generated stegotext variants.

The result should contain:

```text
exactly consistent candidates
ranked candidate matches
number of observations compared
number of matches
number of contradictions
number of erasures
per-channel evidence
ambiguity count
whether the ranking is probabilistic or merely distance-based
```

The library should avoid calling a distance score a probability unless it has a calibrated error model.

### 18.4 Efficient filtering

For thousands or millions of candidates, the implementation can precompute or index encoded candidate codewords. Known bit positions can then intersect candidate sets efficiently rather than decoding each candidate from scratch.

### 18.5 Excerpts and deletion

A true partial excerpt is harder than a full message with erased variants. The decoder may no longer know codeword positions.

Possible strategies include:

1. **Original-cover alignment:** The caller supplies the original cover text. The library canonicalizes the excerpt, locates it within the cover, and maps surviving local sites to global site indices.
2. **Candidate-text comparison:** The caller retains the 1,000 generated variants. The library aligns the leaked fragment against their canonicalized text and compares only the overlapping sites.
3. **Local stable site identifiers:** A site identifier is derived from canonical surrounding text plus an occurrence index. This can survive removal of unrelated sections but must handle repeated phrases and edits.
4. **Chunked self-synchronizing frames:** The payload or fingerprint is repeated across paragraphs or blocks, each block carrying a local header or index.
5. **Sequence alignment:** Channel observations are aligned as symbol sequences rather than assumed to have fixed positions.
6. **Insertion/deletion codes:** A later advanced feature may use codes designed for synchronization errors.

The first release should state clearly which partial-text model it supports. Returning unknown bits is sufficient for normalized sites in an otherwise intact text, but not for arbitrary excerpts.

### 18.6 Candidate matching is not the same as ECC

Error correction attempts to recover one intended codeword from a noisy observation. Candidate identification asks which members of a known finite set could have produced the observation. Candidate identification can succeed even when general decoding cannot.

This separation is one of the important design decisions from the conversation.

---

## 19. Fingerprinting workflow

A recipient-fingerprinting application can use the library as follows.

### 19.1 Preparation

1. Author one cover document.
2. Select a codec configuration and profile.
3. Run capacity analysis.
4. Allocate one opaque payload per recipient.
5. Store the mapping from payload to recipient in an application database.
6. Generate one stegotext variant per recipient.
7. Store the codec configuration and library version used.

### 19.2 Distribution

Each recipient receives a visually or semantically equivalent document containing a distinct payload.

The core library is not responsible for sending the copies. Email, web delivery, file download, or another application layer handles distribution.

### 19.3 Recovery

When a copy is found:

1. Run `decode` using the stored codec configuration.
2. If a complete authenticated payload is recovered, resolve it in the recipient database.
3. If recovery is partial, run `identify` over the known payload set or generated variants.
4. Review the candidate list, evidence, and ambiguity.
5. Avoid asserting a unique source when multiple candidates remain.

### 19.4 Uniqueness and collision checks

An `encode_many` convenience API could preflight:

- whether all payloads fit;
- whether all resulting codewords are distinct;
- minimum pairwise distance among fingerprints;
- expected candidate ambiguity after losing selected channels;
- whether the chosen redundancy is sufficient for the desired number of recipients.

This would be especially useful for the 1,000-copy scenario.

---

## 20. Public API proposal

The precise naming is open, but the following surface captures the desired workflow.

### 20.1 Codec object

```python
codec = TextSteganographyCodec(config)
```

The object compiles and validates the configuration, resolves channel conflicts, and exposes a stable `codec_id`.

### 20.2 Analyze

```python
report = codec.analyze(text)
```

`CapacityReport` should include:

```text
total sites
sites by channel
radix distribution
raw theoretical bits
realizable packed bits
framing overhead
integrity overhead
error-correction overhead
synchronization overhead
usable payload bits and bytes
maximum distinct payloads
warnings
optional detailed site map
```

The encoder should never silently truncate a payload. It should reject payloads larger than usable capacity.

### 20.3 Encode

```python
result = codec.encode(text, payload)
```

`EncodeResult` may contain:

```text
text
payload size
sites used
unused capacity
codec_id
frame version
channel statistics
warnings
optional debug manifest
```

The encoded text should be directly accessible. An optional manifest is for debugging and audit; ordinary decoding should not depend on it.

### 20.4 Decode

```python
result = codec.decode(encoded_text)
```

This returns the structured `DecodeResult` described earlier.

### 20.5 Verify

```python
result = codec.verify(encoded_text, expected_payload)
```

This reports whether the expected payload is present, absent, contradicted, or only partially supported.

### 20.6 Identify

```python
matches = codec.identify(
    observed_text,
    candidates=candidate_payloads,
    cover_text=original_text,
)
```

This filters and ranks candidate payloads.

### 20.7 Inspect

```python
inspection = inspect_text(text, channels=None)
```

An inspection helper can report:

- unusual or invisible code points;
- likely channel variants;
- Unicode names and positions;
- mixed scripts;
- normalization differences;
- capacity under a proposed configuration.

Inspection is useful for debugging and for understanding what a transport preserved.

### 20.8 Optional canonicalize or strip

A later helper may canonicalize selected channel variants back to a neutral representation. This can help test how easily a watermark can be removed and can provide a clean comparison form. It should not be conflated with decoding.

---

## 21. Script and repertoire system

A modular repertoire layer should control which code points are allowed.

### 21.1 Why “repertoire” is better than “alphabet”

“Alphabet” may refer to English letters, to an encoding symbol set, or to all characters in a script. The library needs exact machine-readable allowlists and policies.

### 21.2 Repertoire policies

Possible policies include:

```text
ASCII only
Latin script only
same-script substitutions only
punctuation variants only
no invisible controls
no bidirectional controls
no joiners
no nonbreaking whitespace
explicit Unicode block allowlist
explicit code-point allowlist
identifier-safe only
natural-language text only
```

### 21.3 Channel declarations

Each channel should declare:

- source scripts it recognizes;
- target scripts it may emit;
- language-sensitive behavior;
- whether it crosses scripts;
- whether it introduces format controls;
- normalization behavior;
- known font or rendering caveats;
- suitability for identifiers, prose, markup, or code.

### 21.4 Font and renderer dependence

Two code points that look identical in one font may be distinguishable in another. The documentation should use “confusable” or “visually similar” rather than universally “identical” unless the equivalence is defined by the carrier’s canonical model.

---

## 22. Robustness and threat models

The project should not use one undifferentiated idea of robustness.

### 22.1 Benign transformation model

The text passes through ordinary applications that may normalize or rewrite it without trying to remove a watermark. Error correction and compatibility profiles primarily address this case.

### 22.2 Adversarial removal model

An adversary knows or suspects that text contains a fingerprint and deliberately normalizes punctuation, strips format controls, rewrites the text, or retypes it. Many character-level channels are easy to destroy. The library should make no stronger claim than the chosen channel and threat model justify.

### 22.3 Partial disclosure model

Only a subset of the text is disclosed. Repetition, chunking, interleaving, local anchors, and candidate identification are relevant here.

### 22.4 Collusion model

Two or more recipients compare their copies and combine differences to obscure the source. Simple embedded recipient IDs are not necessarily collusion-resistant. Supporting this would require a dedicated fingerprint-code layer and is a future research area.

### 22.5 Detection model

A third party may inspect code points and discover unusual Unicode usage. Stealth, capacity, compatibility, and robustness trade against one another. A channel that is visually subtle may still be trivial for a machine to detect.

---

## 23. Safety, usability, and interoperability warnings

Some channels can create real operational problems. The library should provide clear warnings rather than treating steganographic capacity as the only criterion.

Potential effects include:

- broken exact search;
- broken copy/paste;
- altered line wrapping;
- altered sorting or tokenization;
- mixed-script security warnings;
- inaccessible screen-reader behavior;
- code compilation or identifier changes;
- malformed markup;
- changed bidirectional display;
- email spam or security filtering;
- diff noise;
- formatter churn;
- font-dependent visual differences;
- unexpected normalization;
- plagiarism or provenance disputes if confidence is overstated.

Risky channels should be explicitly opt-in. Diagnostic output should identify exactly which characters were introduced.

---

## 24. Compatibility testing

The carrier/transport matrix should be based on empirical tests wherever practical.

### 24.1 Round-trip test model

A test can:

1. generate diagnostic cover text containing many site types;
2. encode a known payload;
3. pass the text through a transport;
4. retrieve the result;
5. compare literal code points;
6. decode;
7. measure symbol survival, errors, erasures, insertions, and deletions.

### 24.2 Compatibility metrics

Useful metrics include:

```text
raw site survival rate
known-symbol recovery rate
erasure rate
substitution rate
insertion/deletion rate
full payload recovery rate
candidate-set size after recovery
visible-difference warnings
```

### 24.3 A transport probe

A valuable future feature is a user-run **transport probe**. The library generates a diagnostic sample. The user copies or sends it through the actual application chain and feeds the result back. The library then recommends channels based on measured survival rather than a generic claim.

### 24.4 Versioned evidence

Platform behavior changes. Profiles should record the software version, date, and exact operation tested whenever possible. “Works in email” is too broad; “survived a specific plain-text compose/send/copy path under a tested client version” is a more honest claim.

---

## 25. Architecture and package layout

A possible package structure is:

```text
text_steganography/
    __init__.py
    codec.py
    config.py
    models.py

    core/
        planner.py
        site_ordering.py
        symbol_packing.py
        observations.py
        canonicalization.py
        conflicts.py

    payload/
        framing.py
        integrity.py
        codecs.py
        transforms.py

    ecc/
        protocol.py
        none.py
        adapters/
            hamming.py
            reed_solomon.py
            bch.py

    channels/
        punctuation.py
        unicode_normalization.py
        homoglyphs.py
        invisible/
            zero_width.py
            joiners.py
            variation_selectors.py
            directionality.py
        whitespace/
            unicode_spaces.py
            structural.py
            line_endings.py
        markup/
            html_entities.py
            html_ast.py
            markdown_ast.py
        source_code/
            base.py
            python.py
            javascript.py

    repertoires/
        policies.py
        latin.py
        greek.py
        cyrillic.py
        punctuation.py
        unicode_data.py

    carriers/
        plain_text.py
        markdown.py
        html.py
        source_code.py
        docx.py
        pdf.py

    profiles/
        model.py
        registry.py
        plain_text.py
        markdown_git.py
        html_email.py
        social.py
        source_code.py

    identify/
        candidate_index.py
        alignment.py
        ranking.py
        reports.py

    inspect/
        unicode_report.py
        channel_detection.py

    cli/
        main.py

    tests/
        vectors/
        transport_fixtures/
        property_tests/
```

This is a conceptual decomposition, not a requirement to implement every directory immediately.

---

## 26. Core internal data model

A clean internal representation will make partial decoding and extensibility much easier.

### 26.1 Embedding plan

Before encoding, the codec builds an `EmbeddingPlan`:

```text
canonical cover text
ordered list of sites
channel ownership of each site
site radix
site variants
stable identifiers
capacity summary
packing plan
warnings
```

### 26.2 Codeword

The payload pipeline produces a `Codeword`:

```text
framed payload
integrity bits
ECC bits or symbols
packing metadata implied by config
```

### 26.3 Observation vector

Decoding produces an `ObservationVector` whose entries can be:

```text
known symbol
erased symbol
ambiguous set of symbols
invalid symbol
missing site
inserted/unmapped observation
```

This richer representation is important. Reducing everything immediately to a guessed bitstream would throw away information needed for erasure-aware correction and candidate filtering.

### 26.4 Results

Public results should be immutable or easily serializable dataclasses so they can be logged, tested, and consumed by other agents or applications.

---

## 27. Rich-carrier adapters

The project should keep a Unicode-string core while allowing format-specific adapters.

A `CarrierAdapter` might:

1. parse the carrier;
2. expose eligible text nodes or spans;
3. prevent changes in protected contexts;
4. apply channel substitutions;
5. serialize the result;
6. supply transport-specific metadata.

Examples:

- An HTML adapter should avoid scripts, styles, URLs, identifiers, and unsafe attributes unless explicitly enabled.
- A Markdown adapter should understand code fences, inline code, links, and raw HTML.
- A source-code adapter should use a real parser or tokenizer.
- A DOCX adapter should work with text runs and preserve document structure.
- A PDF adapter may need a completely different model and should not be promised early.

Carrier adapters and steganographic channels should remain separate. The adapter says where text may be touched; the channel says how a particular site can encode symbols.

---

## 28. Configuration example

A future user-facing configuration could resemble:

```python
from text_steganography import CodecConfig
from text_steganography.channels import (
    ApostropheVariants,
    CanonicalUnicodeVariants,
    UnicodeSpaceVariants,
    ZeroWidthSpaceChannel,
)
from text_steganography.repertoires import RepertoirePolicy
from text_steganography.ecc import ErrorCorrectionConfig

config = CodecConfig(
    version=1,
    channels=[
        ApostropheVariants(mode="conservative"),
        CanonicalUnicodeVariants(normal_forms=("NFC", "NFD")),
        UnicodeSpaceVariants(allow_nonbreaking=False),
        ZeroWidthSpaceChannel(enabled=False),
    ],
    repertoire=RepertoirePolicy(
        scripts={"Latin"},
        allow_cross_script=False,
        allow_bidi_controls=False,
        allow_joiners=False,
    ),
    packing="power_of_two",
    framing="length_crc_v1",
    error_correction=ErrorCorrectionConfig(
        codec="external_adapter_name",
        parameters={"strength": "moderate"},
    ),
    profile="plain_text_conservative",
)
```

The exact classes and names are placeholders. The important property is that the configuration is explicit, serializable, versioned, and shared by encoding and decoding.

---

## 29. End-to-end example

Consider a document containing five apostrophe-like sites. Suppose the selected punctuation channel safely provides four variants at each site.

Raw capacity is:

```text
5 sites × 2 bits/site = 10 bits
```

Ten bits can represent 1,024 raw values, so in a toy example it is just enough to assign distinct identifiers to 1,000 recipients.

However, there is no room for:

- frame version;
- length;
- checksum;
- error correction;
- synchronization;
- future compatibility.

The capacity analyzer should therefore reject a robust 1,000-recipient configuration even though the naive raw entropy appears sufficient.

A longer document may provide 80 raw bits across several channels. The application embeds an opaque 16-bit recipient token plus framing and error correction. Each recipient receives a different stegotext.

Later, one paragraph appears in a forum post. Some curly apostrophes have been normalized and all zero-width characters have been stripped. The workflow is:

1. Canonicalize and align the paragraph with the original cover text.
2. Observe surviving punctuation and normalization-form symbols.
3. Mark stripped sites as erasures.
4. Attempt ECC decoding.
5. If the full token is not recovered, compare the observation vector against all 1,000 expected recipient codewords.
6. Return, for example, three exactly consistent candidates and a ranked list based on the available evidence.
7. Report that a unique attribution is not possible.

This is the desired graceful degradation.

---

## 30. Testing strategy

The project needs unusually strong tests because Unicode and transport behavior are subtle.

### 30.1 Core round-trip properties

For every supported channel and valid input:

```text
decode(encode(text, payload, config), config) == payload
```

when capacity is sufficient and no transport transformation occurs.

### 30.2 Invariant properties

For each channel:

```text
canonicalize(encode(text, payload)) == canonicalize(text)
```

or the appropriate rendered/semantic invariant defined by that channel.

### 30.3 Determinism

The same inputs must produce the same output under the same versioned configuration.

### 30.4 Capacity correctness

Tests should verify that:

- reported capacity is not exceeded;
- all claimed symbol combinations are reachable;
- insufficient payload space raises an explicit error;
- no silent truncation occurs;
- overhead calculations match actual frames and codewords.

### 30.5 Conflict tests

Overlapping channels must produce deterministic resolution or a clear configuration error.

### 30.6 Unicode normalization tests

Every Unicode-based channel should be tested under NFC, NFD, NFKC, and NFKD transformations, even when the expected result is destruction of the watermark.

### 30.7 Error-model tests

Inject:

- symbol substitutions;
- site erasures;
- stripped characters;
- inserted characters;
- deleted spans;
- reordered paragraphs;
- complete channel loss.

Verify both decode behavior and candidate filtering.

### 30.8 Property-based and fuzz testing

Property-based tests should generate Unicode strings, combining sequences, punctuation contexts, and malformed inputs. The library must not crash, corrupt unrelated text, or misreport success.

### 30.9 Golden vectors

Release stable golden vectors containing:

```text
cover text
configuration
payload
expected stegotext
expected observations
expected decoded payload
```

These protect long-term compatibility.

### 30.10 Transport fixtures

Maintain a corpus of before/after samples from real transports. Profiles should be tied to this evidence.

---

## 31. Documentation plan

The documentation is as important as the code.

It should contain:

1. **Conceptual introduction:** steganography, watermarking, fingerprinting, payloads, channels, carrier, and transport.
2. **Quick start:** analyze, encode, decode, identify.
3. **Channel catalog:** exact mechanism, capacity, invariants, risks, and common failure modes.
4. **Carrier/transport matrix:** simple recommendations with explanations.
5. **Capacity guide:** symbols, entropy, overhead, and the 1,000-recipient example.
6. **Error-correction guide:** errors, erasures, synchronization, and codec adapters.
7. **Partial-identification guide:** candidate filtering and ranking.
8. **Unicode safety guide:** scripts, confusables, normalization, invisible characters, and accessibility.
9. **Threat-model guide:** benign transformation, adversarial removal, excerpts, and collusion.
10. **Configuration reference:** schema, versioning, and reproducibility.
11. **Testing transports:** how to run a probe through a real system.
12. **Limitations:** no guarantee of invisibility, survival, confidentiality, or unique attribution.

Warnings should be plain and direct. The user should be able to understand not only that a channel is fragile, but *why*.

---

## 32. Error-correction repository decision

The conversation reached a conditional architectural decision:

- The steganography package should expose a generic, pluggable error-correction interface.
- It should first use or wrap existing implementations.
- It should not build a large coding-theory subsystem inside the steganography repository.
- If a reusable abstraction or missing implementation genuinely needs to be built, that work should be split into a separate repository/package so it can have an independent scope and be reused elsewhere.

This avoids premature repository proliferation while preserving a clean dependency boundary.

---

## 33. Recommended initial implementation

The conversation did not lock an MVP, but the following sequence is a practical interpretation of the design.

### Phase 1: Unicode-string core

Implement:

- versioned configuration;
- channel protocol;
- deterministic site planning;
- capacity analysis;
- simple binary or power-of-two packing;
- byte payload framing;
- checksum/integrity validation;
- encode and decode;
- structured observations;
- inspect utility;
- strong golden-vector and property tests.

Begin with a small set of channels:

- conservative punctuation variants;
- canonical-equivalent Unicode sequences;
- Unicode-space variants;
- line endings for file-oriented tests.

Keep the following experimental and opt-in:

- zero-width insertion;
- joiners or format controls;
- cross-script homoglyphs.

### Phase 2: Error correction and identification

Add:

- generic ECC adapter protocol;
- at least one mature external codec adapter;
- erasure-aware observation mapping where supported;
- interleaving;
- candidate filtering over known payloads;
- ranked matching and ambiguity reporting;
- `encode_many` fingerprint preflight.

### Phase 3: Fragment alignment and profiles

Add:

- original-cover alignment;
- local site anchors;
- chunked or repeated fingerprints;
- transport probe;
- empirical compatibility profiles;
- carrier/transport matrix generation.

### Phase 4: Carrier adapters

Add parser-aware support for:

- Markdown;
- HTML;
- selected source languages;
- possibly DOCX.

Treat Google Docs and PDF as separate investigations because their transport and representation models are substantially more complicated.

### Phase 5: Advanced capacity and tracing

Consider:

- mixed-radix packing;
- insertion/deletion-aware codes;
- keyed placement;
- authenticated or encrypted payload transforms;
- collusion-resistant fingerprint codes;
- rich-document formatting channels.

---

## 34. Open design questions

The following questions should remain visible for the implementation agent.

### 34.1 What exact invariant does “lossless” mean?

Should the core promise canonical-text equivalence, visual equivalence, semantic equivalence, or a channel-specific invariant? The recommended answer is channel-specific declarations plus profile-level requirements.

### 34.2 Must ordinary decoding work without the original cover text?

The intended answer is yes for full, intact stegotext. Channels that cannot do this must declare the limitation. Fragment identification may still require the original cover text or candidate corpus.

### 34.3 How should arbitrary-radix sites be packed?

Start simple with power-of-two packing, or implement mixed-radix packing immediately? The architecture should not foreclose the latter.

### 34.4 What frame overhead is mandatory?

At minimum, length and integrity are useful. Embedding a version or codec identifier improves diagnostics but costs capacity.

### 34.5 Which external error-correction implementation should be used?

This requires a focused dependency evaluation. Requirements include licensing, maintenance, Python support, error and erasure handling, and compatibility with partial observations.

### 34.6 How should fragment synchronization work?

Original-cover alignment is the simplest robust starting point. Self-synchronizing blocks are more autonomous but consume capacity.

### 34.7 Should placement be keyed?

A secret seed could select or permute sites, making the watermark harder to inspect or modify. It also complicates reproducibility, debugging, and partial alignment. This is optional and was not part of the original minimal idea.

### 34.8 How should profiles be maintained?

Profiles may be shipped as versioned data files, generated from transport tests, or maintained in a separate compatibility repository.

### 34.9 How should channel reliability influence ranking?

A simple candidate filter can count contradictions. A more advanced ranker may weight channels by empirical survival rates. Probability claims require calibration.

### 34.10 How much rich-document support belongs in the main package?

A small adapter API may live in core while heavy DOCX, PDF, or language-parser dependencies are optional extras.

### 34.11 How should collusion be handled?

Simple per-recipient IDs are not a complete collusion-resistant traitor-tracing system. This should be stated explicitly and researched separately if needed.

### 34.12 How should privacy be handled?

Embedding a raw customer or employee ID may expose that identifier to anyone who discovers the encoding. Opaque random tokens are likely a safer application pattern.

---

## 35. Acceptance criteria for the first useful release

A first public release should be considered successful when it can demonstrate all of the following:

1. A user can define a versioned codec with multiple deterministic channels.
2. `analyze` reports raw and usable capacity with per-channel detail.
3. The encoder refuses an oversized payload rather than truncating it.
4. A byte payload can be encoded into Unicode text and decoded with the same configuration.
5. Decoding returns structured diagnostics, including erasures or ambiguous observations.
6. At least one optional error-correction adapter works behind a generic interface.
7. A partial observation can filter a known candidate set.
8. Risky channels are opt-in and generate explicit warnings.
9. Golden test vectors guarantee deterministic behavior.
10. Documentation defines carrier and transport and provides an initial compatibility matrix.
11. The package is usable as a Python library without requiring email, social-platform, or document-service integrations.
12. The design allows later carrier adapters and mixed-radix packing without replacing the public model.

---

## 36. Compact design principles

The entire project can be summarized by the following principles:

- Use the word **steganography** for the project’s central concept.
- Keep the system deterministic and representation-based.
- Do not use linguistic or stylometric rewriting in the core.
- Treat each textual choice as a symbol-bearing channel.
- Separate payload, framing, error correction, packing, and channel application.
- Make capacity analysis first-class.
- Let the user choose channels; make profiles advisory.
- Define carrier and transport separately.
- Use script and character repertoire rather than an overloaded notion of alphabet.
- Return payload bytes and rich diagnostics, not just a hash.
- Preserve unknown and ambiguous observations.
- Treat candidate identification as separate from error correction.
- Support filtering and ranking among known fingerprints when full decoding fails.
- Prefer existing error-correction implementations.
- Split a generic ECC project into another repository only if substantial new reusable work is required.
- Version every mapping and configuration needed for future decoding.
- Be conservative with homoglyphs, invisible controls, and other risky Unicode techniques.
- Document failure modes as carefully as successful examples.
- Never claim unique provenance when the evidence supports multiple candidates.

---

## 37. Final project statement

Build a widely available Python library for **modular, deterministic text steganography**. The library will let users embed small arbitrary payloads into the literal representation of text by selecting from explicit, configurable textual variants. It will support multiple channel families, estimate the entropy and usable capacity available in a particular cover text, apply framing and optional error correction, decode complete or partial observations, and identify which known fingerprinted copies are compatible with surviving evidence.

The system will treat textual format, transport behavior, Unicode repertoire, error models, and candidate attribution as distinct but composable concerns. It will provide simple carrier/transport recommendations without taking configuration control away from the user. Its architecture will favor stable versioned codecs, transparent diagnostics, empirical compatibility testing, conservative defaults, and clear limitations.

The motivating example is the generation of 1,000 visually equivalent copies of one message, each carrying a different hidden payload. A complete leaked copy should decode to its payload. A damaged or partial copy should yield a structured observation that can filter or rank the 1,000 candidates. The same machinery should remain general enough for provenance markers, distribution tracking, document lineage, application-defined metadata, and future carrier-specific adapters.

The result should be a focused steganography library rather than a collection of unrelated tricks: payload-independent channels, channel-independent error correction, explicit entropy accounting, and principled degradation when the hidden signal is only partly preserved.
