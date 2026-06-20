import sqlite3

DB_PATH = "external/core_data/html_web_basics.db"

concepts = []
def create_concept_resources_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_resources (
            concept_id TEXT PRIMARY KEY,
            topic TEXT,
            base_content TEXT,
            examples TEXT,
            key_points TEXT,
            misconceptions TEXT,
            real_world_use TEXT,
            next_concept_link TEXT
        );
    """)

# ─────────────────────────────────────────────
# H1: What is HTML
# ─────────────────────────────────────────────
concepts.append({
    "concept_id": "H1",
    "topic": "What is HTML",
    "base_content": """
HTML stands for HyperText Markup Language. It is the standard language used to create and structure content on the web. HTML is not a programming language — it is a markup language. It describes the structure and meaning of content using a system of elements represented by tags.

Every web page you see in a browser is built on HTML. When you visit a website, the browser downloads an HTML file, reads it, and renders it visually on screen. HTML tells the browser what each piece of content is — a heading, a paragraph, an image, a link — and the browser decides how to display it.

What HyperText means:
HyperText refers to text that contains links to other documents or resources. These links allow you to jump from one page to another — this is the foundation of the web itself. The ability to navigate between pages through links is what makes the web a connected network of information rather than isolated documents.

What Markup means:
Markup means annotating content with special symbols or tags to add meaning to it. HTML wraps content in tags like <h1> or <p> to tell the browser what role that content plays. A heading is not just large text — it is semantically a heading. A paragraph is not just a block of text — it is semantically a paragraph.

How HTML works:
HTML uses a system of elements. Each element typically has an opening tag, content, and a closing tag. The browser reads these elements and builds a visual page from them.

Basic structure of an HTML page:
<!DOCTYPE html>
<html>
  <head>
    <title>My First Page</title>
  </head>
  <body>
    <h1>Hello, World!</h1>
    <p>This is a paragraph.</p>
  </body>
</html>

The DOCTYPE declaration:
The line <!DOCTYPE html> tells the browser that this document follows the HTML5 standard. It must appear at the very top of every HTML file. Without it, browsers may enter "quirks mode" and render the page inconsistently.

The <html> element:
The root element that wraps all content on the page. Everything in an HTML document lives inside this element.

The <head> element:
The head section contains metadata — information about the document that is not displayed directly on the page. This includes the page title, character encoding, links to stylesheets, and other settings.

The <body> element:
The body section contains all content that is actually displayed in the browser — headings, paragraphs, images, links, forms, and everything else the user sees and interacts with.

How browsers render HTML:
When a browser loads an HTML page, it:
1. Reads the HTML file character by character
2. Parses the tags and builds a tree-like structure called the DOM (Document Object Model)
3. Applies styling (CSS) to the DOM
4. Renders the final visual result on screen

HTML, CSS, and JavaScript:
HTML defines structure and content.
CSS (Cascading Style Sheets) controls appearance — colors, fonts, layout, spacing.
JavaScript adds behavior and interactivity — responding to clicks, updating content dynamically.
These three work together to build everything you see on the web. HTML is the foundation that the other two build upon.

HTML versions:
HTML has evolved over time. The current standard is HTML5, released in 2014 and continuously updated. HTML5 introduced semantic elements, native audio and video support, the canvas element for drawing, and many modern web features. Writing <!DOCTYPE html> at the top of your file tells the browser to use HTML5.
""",
    "examples": """
Example 1 — Minimal valid HTML page:
<!DOCTYPE html>
<html>
  <head>
    <title>My Page</title>
  </head>
  <body>
    <h1>Welcome</h1>
    <p>This is my first web page.</p>
  </body>
</html>
# The browser renders: a large heading "Welcome" followed by a paragraph.

Example 2 — HTML with multiple content types:
<!DOCTYPE html>
<html>
  <head>
    <title>About HTML</title>
  </head>
  <body>
    <h1>What is HTML?</h1>
    <p>HTML is the language of the web.</p>
    <h2>Key Facts</h2>
    <p>It uses tags to structure content.</p>
  </body>
</html>
# Two heading levels and two paragraphs — browser renders them in order.

Example 3 — The role of DOCTYPE:
# Without DOCTYPE:
<html>
  <body><p>Hello</p></body>
</html>
# Browser may use quirks mode — inconsistent rendering.

# With DOCTYPE (correct):
<!DOCTYPE html>
<html>
  <body><p>Hello</p></body>
</html>
# Browser uses standards mode — predictable, consistent rendering.

Example 4 — Real-world analogy:
# HTML is like the skeleton of a house.
# CSS is the paint, wallpaper, and decoration.
# JavaScript is the electricity and moving parts.
# The skeleton defines what rooms exist and how they connect.
# Without it, there is nothing for CSS or JavaScript to work with.
""",
    "key_points": """
- HTML stands for HyperText Markup Language — it structures web content
- HTML is a markup language, not a programming language
- HyperText means content linked to other documents through hyperlinks
- Markup means annotating content with tags to define its role and meaning
- Every HTML page has a DOCTYPE declaration, html, head, and body
- <!DOCTYPE html> declares HTML5 and must appear at the very top
- The head contains metadata not shown on screen
- The body contains all visible content
- Browsers parse HTML into a DOM tree and then render it visually
- HTML defines structure, CSS defines appearance, JavaScript defines behavior
- HTML5 is the current standard — it introduced semantic elements, audio, video, and canvas
- HTML is the foundation of every web page — CSS and JavaScript depend on it
""",
    "misconceptions": """
- "HTML is a programming language" — HTML is a markup language. It has no logic, no conditions, no loops, and no variables. It describes structure, not behavior. JavaScript is the programming language of the web.
- "DOCTYPE is optional" — Omitting DOCTYPE causes browsers to enter quirks mode, which produces inconsistent rendering across browsers. Always include it.
- "The head section is unimportant" — The head contains critical metadata including the character encoding, page title shown in browser tabs, links to CSS, SEO metadata, and viewport settings. It is essential.
- "HTML alone makes websites look good" — HTML provides only structure. Visual appearance requires CSS. Without CSS, all text is unstyled black on white with default browser formatting.
- "You need to memorize all HTML tags" — HTML has many tags but most real-world development uses a small core set. Understanding structure and semantics matters more than memorizing every tag.
- "HTML5 is a new language" — HTML5 is the current version of HTML, not a separate language. It added features and semantic elements to the existing HTML standard.
""",
    "real_world_use": """
- Every website and web application uses HTML as its structural foundation
- Search engines read HTML to index page content and understand page structure
- Screen readers for visually impaired users interpret HTML structure to navigate pages
- Email clients render HTML emails using a subset of the HTML standard
- Browser developer tools display the HTML DOM to help developers inspect and debug pages
- Web scrapers parse HTML documents to extract structured data from websites
""",
    "next_concept_link": """
HTML defines what content exists on a page. The next concept — HTML Tags and Elements — goes deeper into the building blocks of HTML: how tags work, how elements are structured, and how the browser interprets the nesting and hierarchy of elements to build a complete page.
"""
})

# ─────────────────────────────────────────────
# H2: HTML Tags and Elements
# ─────────────────────────────────────────────
concepts.append({
    "concept_id": "H2",
    "topic": "HTML Tags and Elements",
    "base_content": """
Tags are the syntax of HTML. An element is the complete unit consisting of an opening tag, content, and a closing tag. Tags are written using angle brackets and tell the browser what type of content follows.

Anatomy of an element:
<tagname>content goes here</tagname>

Opening tag: <tagname> — signals the start of the element
Content: the text or nested elements inside
Closing tag: </tagname> — signals the end of the element. The closing tag always has a forward slash before the tag name.

Example:
<p>This is a paragraph.</p>
<h1>This is a heading.</h1>

Void elements (self-closing):
Some elements do not wrap content — they stand alone. These are called void elements. They have only an opening tag and no closing tag.
<br>      — line break
<hr>      — horizontal rule (dividing line)
<img>     — image
<input>   — form input field
<meta>    — metadata in head
<link>    — external resource link

In HTML5, these do not require a trailing slash. Writing <br> and <br/> are both valid.

Block-level elements:
Block elements take up the full width available and always start on a new line. They create visible blocks of content.
<h1> to <h6>  — six levels of headings
<p>            — paragraph
<div>          — generic container block
<ul>           — unordered list
<ol>           — ordered list
<li>           — list item
<table>        — table
<form>         — form container
<header>       — page header section
<footer>       — page footer section
<section>      — document section
<article>      — self-contained content

Inline elements:
Inline elements only take up as much width as their content needs. They do not start on a new line and flow within surrounding text.
<span>    — generic inline container
<a>       — hyperlink
<strong>  — bold with semantic importance
<em>      — italic with semantic emphasis
<img>     — image (inline by default)
<br>      — line break
<input>   — form input (inline)

Nesting elements:
HTML elements can be nested inside each other to build structure. The inner element must be fully closed before the outer element closes. Improper nesting produces malformed HTML.

Correct nesting:
<p>This is <strong>important</strong> text.</p>

Incorrect nesting (broken):
<p>This is <strong>important</p></strong>

The DOM tree:
When the browser reads HTML, it builds a tree from nested elements. Each element is a node. Parent elements contain child elements. The tree structure determines how elements relate and interact.

<!DOCTYPE html>
<html>
  <head>
    <title>Page</title>
  </head>
  <body>
    <h1>Heading</h1>
    <p>Paragraph with <strong>bold</strong> text.</p>
  </body>
</html>

DOM tree:
html
├── head
│   └── title — "Page"
└── body
    ├── h1 — "Heading"
    └── p
        ├── "Paragraph with "
        ├── strong — "bold"
        └── " text."

Heading hierarchy:
Headings run from h1 to h6. h1 is the most important — there should be only one h1 per page. Headings define the outline of the document and are critical for accessibility and SEO.
<h1>Main Title</h1>
<h2>Section Title</h2>
<h3>Subsection Title</h3>

Paragraphs and whitespace:
Browsers ignore extra whitespace in HTML source. Multiple spaces and line breaks in your code collapse to a single space in the rendered output. Use <br> for a line break and <p> for paragraph separation.
<p>This   has   extra   spaces.</p>
<!-- Renders as: "This has extra spaces." -->

The <div> and <span> elements:
<div> is a generic block container with no default meaning. It is used to group elements for layout or styling.
<span> is a generic inline container with no default meaning. It is used to apply styles or target specific text.

<div class="card">
  <h2>Title</h2>
  <p>Content with <span class="highlight">highlighted</span> word.</p>
</div>

Comments in HTML:
HTML supports comments for notes in code. They are not displayed in the browser.
<!-- This is a comment -->
<p>This is visible.</p>
<!-- TODO: add image here -->
""",
    "examples": """
Example 1 — Basic elements:
<!DOCTYPE html>
<html>
  <body>
    <h1>Main Heading</h1>
    <h2>Sub Heading</h2>
    <p>A paragraph of text.</p>
    <p>Another paragraph.</p>
  </body>
</html>
# Each element displays on its own line. Headings are larger by default.

Example 2 — Block vs inline:
<p>This is a <strong>block</strong> paragraph.</p>
<p>This is <em>another</em> paragraph.</p>
# Both p tags start on new lines (block). strong and em flow inline within text.

<span>First</span><span>Second</span>
# Both spans appear side by side — they are inline.

Example 3 — Nesting and DOM:
<div>
  <h2>Card Title</h2>
  <p>This card has a <a href="#">link</a> inside.</p>
</div>
# div contains h2 and p. p contains an inline a element.

Example 4 — Void elements:
<p>Line one.<br>Line two.</p>
<hr>
<img src="photo.jpg">
<input type="text">
# br causes a line break within the paragraph.
# hr renders a horizontal dividing line.
# img and input have no closing tag.

Example 5 — Comments:
<!-- Navigation will go here -->
<h1>Welcome</h1>
<!-- TODO: add hero image -->
<p>Content below the heading.</p>
# Comments are invisible in the browser but visible in source code.
""",
    "key_points": """
- A tag is the syntax: <tagname> and </tagname>
- An element is the complete unit: opening tag + content + closing tag
- Void elements have no closing tag and no content: <br>, <img>, <input>, <hr>
- Block elements start on a new line and take full width: h1-h6, p, div, ul, ol
- Inline elements flow within text and take only their content width: a, strong, em, span
- Elements must be properly nested — inner elements closed before outer elements
- The browser parses HTML into a DOM tree of nested nodes
- h1 through h6 define document outline — only one h1 per page is best practice
- Browsers collapse extra whitespace — use br for line breaks, p for paragraphs
- div is a generic block container; span is a generic inline container
- HTML comments use <!-- --> syntax and are not rendered in the browser
- Correct nesting is required for valid, predictable HTML rendering
""",
    "misconceptions": """
- "All elements need a closing tag" — Void elements like <br>, <img>, <hr>, and <input> have no closing tag. Adding one would create invalid HTML.
- "<div> is just a container with no purpose" — div is a structural grouping tool essential for layout. It has no visual meaning itself but enables CSS layout systems like flexbox and grid.
- "You can use as many h1 tags as you want" — Best practice and accessibility guidelines recommend one h1 per page as the main title. Multiple h1 tags confuse screen readers and reduce SEO clarity.
- "Inline and block is just about visual layout" — Block and inline is a fundamental rendering model that affects how elements flow, stack, and can be nested. Understanding it is essential for controlling layout.
- "Whitespace in HTML source is preserved" — Browsers collapse all whitespace to a single space. Indentation and line breaks in your code have no effect on rendered output.
- "Nesting order does not matter" — Improper nesting like <p><strong>text</p></strong> produces invalid HTML. Browsers may attempt to correct it, but the behavior is undefined and unreliable across browsers.
""",
    "real_world_use": """
- Every web page is built by combining block and inline elements in a nested structure
- Heading hierarchy (h1-h6) is read by search engines to understand page content and rank pages
- Screen readers navigate pages using heading structure — improper headings break accessibility
- div and span are the backbone of CSS-based layout in all modern websites
- The DOM tree built from HTML elements is what JavaScript manipulates to create dynamic behavior
- HTML comments are used in team projects to leave notes and TODOs inside source code
""",
    "next_concept_link": """
HTML Tags and Elements establish the core building blocks — how elements are structured, nested, and rendered. The next concept — Attributes and Links — expands elements with additional information. Attributes modify how elements behave or appear, and the anchor element with its href attribute is what creates the hyperlinks that connect the web.
"""
})

# ─────────────────────────────────────────────
# H3: Attributes and Links
# ─────────────────────────────────────────────
concepts.append({
    "concept_id": "H3",
    "topic": "Attributes and Links",
    "base_content": """
Attributes provide additional information about an HTML element. They are placed inside the opening tag and follow the format: name="value". Attributes modify the behavior or appearance of an element, or provide metadata the browser or other systems use.

Syntax of an attribute:
<tagname attribute="value">content</tagname>

Example:
<a href="https://example.com">Click here</a>
href is the attribute name. "https://example.com" is the value.

Rules for attributes:
- Attributes are always written in the opening tag, never the closing tag
- Attribute names are case-insensitive but lowercase by convention
- Attribute values are enclosed in double quotes (single quotes are also valid but double is standard)
- Multiple attributes are separated by spaces

Multiple attributes:
<input type="text" name="username" placeholder="Enter username">

Boolean attributes:
Some attributes do not need a value — their presence alone activates the behavior.
<input type="checkbox" checked>
<input type="text" disabled>
<button disabled>Submit</button>
Writing checked is equivalent to checked="checked". The attribute's existence is what matters.

The id attribute:
id gives an element a unique identifier on the page. No two elements should share the same id. Used to target elements with CSS and JavaScript, and to create anchor links.
<h2 id="about">About Us</h2>

The class attribute:
class assigns one or more style groups to an element. Multiple elements can share the same class. Multiple classes on one element are separated by spaces.
<p class="intro">Welcome.</p>
<p class="intro highlight">Special paragraph.</p>

The style attribute:
style applies inline CSS directly to an element. Generally avoided in favor of external CSS, but useful for quick one-off styling.
<p style="color: red; font-size: 18px;">Red text.</p>

The title attribute:
title provides a tooltip that appears when the user hovers over the element.
<p title="More info">Hover over me.</p>

Hyperlinks — the <a> element:
The anchor element <a> creates a hyperlink. The href attribute specifies the destination.
<a href="https://www.google.com">Go to Google</a>

Link types:
Absolute URL — links to an external website with a full address:
<a href="https://www.wikipedia.org">Wikipedia</a>

Relative URL — links to a file within the same website:
<a href="about.html">About Page</a>
<a href="../contact.html">Contact (one level up)</a>

Anchor link — links to a section within the same page using an id:
<a href="#about">Jump to About Section</a>
...
<h2 id="about">About Us</h2>

Email link — opens the user's email client:
<a href="mailto:hello@example.com">Send Email</a>

Phone link — triggers a phone call on mobile:
<a href="tel:+919876543210">Call Us</a>

The target attribute:
target="_blank" opens the link in a new browser tab.
<a href="https://example.com" target="_blank">Open in new tab</a>

Security note: When using target="_blank", always also add rel="noopener noreferrer" to prevent the new tab from accessing the original page (a security vulnerability called tabnabbing).
<a href="https://example.com" target="_blank" rel="noopener noreferrer">Safe external link</a>

The alt attribute on images (preview):
The alt attribute provides alternative text for images — used by screen readers and shown when the image fails to load.
<img src="photo.jpg" alt="A sunset over the mountains">

Data attributes:
Custom data attributes allow you to store extra data on elements without using hidden fields. They follow the pattern data-* and can be read by JavaScript.
<button data-user-id="42" data-action="delete">Delete</button>

Global attributes:
Some attributes work on any HTML element:
- id — unique identifier
- class — style group
- style — inline CSS
- title — tooltip
- lang — language of the element's content
- tabindex — keyboard navigation order
- hidden — hides the element
- data-* — custom data storage
""",
    "examples": """
Example 1 — Basic attribute usage:
<a href="https://www.python.org">Python Official Site</a>
<img src="logo.png" alt="Company Logo">
<input type="email" placeholder="Enter your email">
# href sets the link destination. alt describes the image. type defines input behavior.

Example 2 — id and class:
<h2 id="contact">Contact</h2>
<p class="intro">Welcome to our page.</p>
<p class="intro highlight">Special announcement here.</p>
# id="contact" uniquely identifies the heading.
# Both paragraphs share class="intro". Second also has "highlight".

Example 3 — All link types:
<!-- External link opening in new tab safely -->
<a href="https://github.com" target="_blank" rel="noopener noreferrer">GitHub</a>

<!-- Internal link -->
<a href="portfolio.html">My Portfolio</a>

<!-- Jump to section on same page -->
<a href="#skills">See My Skills</a>
<h2 id="skills">My Skills</h2>

<!-- Email link -->
<a href="mailto:hello@me.com">Email Me</a>

<!-- Phone link (works on mobile) -->
<a href="tel:+911234567890">Call Me</a>

Example 4 — Boolean attributes:
<input type="checkbox" checked>         <!-- pre-checked -->
<input type="text" disabled>            <!-- cannot be typed in -->
<button disabled>Submit</button>         <!-- cannot be clicked -->

Example 5 — Data attributes used by JavaScript:
<button data-product-id="101" data-action="add-to-cart">Add to Cart</button>

<script>
  const btn = document.querySelector('button');
  console.log(btn.dataset.productId);  // "101"
  console.log(btn.dataset.action);     // "add-to-cart"
</script>
""",
    "key_points": """
- Attributes go inside the opening tag in name="value" format
- Attribute names are lowercase by convention; values use double quotes
- id is unique per page; class can be shared across multiple elements
- href is the core attribute of the <a> element — it sets the link destination
- Absolute URLs include the full address; relative URLs reference files within the site
- Anchor links use href="#id" to jump to a section with a matching id
- target="_blank" opens links in a new tab
- Always pair target="_blank" with rel="noopener noreferrer" for security
- Boolean attributes like checked and disabled work by presence alone — no value needed
- data-* attributes store custom data on elements accessible via JavaScript
- alt on images provides text for screen readers and when images fail to load
- Global attributes (id, class, style, title, hidden) work on any HTML element
""",
    "misconceptions": """
- "id and class do the same thing" — id must be unique per page and targets one element. class groups multiple elements. They serve different purposes for CSS targeting and JavaScript selection.
- "target='_blank' is always safe" — Without rel='noopener noreferrer', new tabs can access and manipulate the original page through the window.opener object, a known security vulnerability.
- "Relative links are always better than absolute links" — Relative links are for internal navigation within the same site. Absolute links are required for external websites. Neither is universally better.
- "Boolean attributes need a value" — Writing disabled="true" or checked="true" is redundant. The presence of the attribute is sufficient. disabled alone is correct.
- "The title attribute is the same as the alt attribute" — title shows a tooltip on hover for any element. alt is specific to images and provides accessibility text for screen readers. They are not interchangeable.
- "Inline style is fine to use everywhere" — Inline styles apply to one element only, cannot be reused, and override external CSS making debugging harder. External CSS stylesheets are always preferred.
""",
    "real_world_use": """
- Navigation menus on every website use anchor elements with href attributes to link pages
- Single-page websites use anchor links with id targets to scroll to sections smoothly
- Login forms use type, name, placeholder, and required attributes on input elements
- Analytics and A/B testing tools use data-* attributes to tag clickable elements for tracking
- Accessibility tools depend on alt attributes on images to describe visual content to blind users
- Email and phone links in mobile websites directly trigger the device's mail and dialer apps
""",
    "next_concept_link": """
Attributes and Links show how elements receive additional information and how pages connect through hyperlinks. The next concept — Images and Lists — covers two of the most common content types in HTML: how to embed visual media with the img element and how to present structured collections of items with ordered and unordered lists.
"""
})

# ─────────────────────────────────────────────
# H4: Images and Lists
# ─────────────────────────────────────────────
concepts.append({
    "concept_id": "H4",
    "topic": "Images and Lists",
    "base_content": """
Images and lists are among the most frequently used content types in HTML. Images embed visual media into a page. Lists organize related items into structured, readable groups.

────────────────────────────────────
IMAGES
────────────────────────────────────

The <img> element:
The img element embeds an image into a web page. It is a void element — it has no closing tag. The two required attributes are src (source) and alt (alternative text).

<img src="photo.jpg" alt="A mountain landscape">

The src attribute:
src specifies the path to the image file. It can be a relative path to a local file or an absolute URL to an image hosted online.
<img src="images/logo.png" alt="Logo">                    <!-- relative path -->
<img src="https://example.com/banner.jpg" alt="Banner">  <!-- absolute URL -->

The alt attribute:
alt provides a text description of the image. It is used by:
- Screen readers for visually impaired users
- Browsers when the image fails to load
- Search engines to understand image content
If the image is purely decorative with no informational value, alt can be left empty (alt="") but must still be present.

Width and height attributes:
Setting width and height on images prevents layout shift while the page loads. The browser reserves space before the image downloads.
<img src="photo.jpg" alt="Photo" width="400" height="300">

Values are in pixels by default. For responsive behavior, width and height are usually set with CSS instead.

Image formats commonly used:
- JPEG (.jpg) — photographs and complex images. Small file size. No transparency.
- PNG (.png) — graphics, logos, screenshots. Supports transparency.
- GIF (.gif) — simple animations. Limited to 256 colors.
- SVG (.svg) — vector graphics. Scales perfectly at any size. Used for icons and logos.
- WebP (.webp) — modern format. Smaller file size than JPEG/PNG with better quality.

The <figure> and <figcaption> elements:
figure wraps an image with a caption. figcaption provides the caption text. This is the semantic way to pair images with descriptions.
<figure>
  <img src="chart.png" alt="Sales chart for Q1">
  <figcaption>Figure 1: Q1 Sales Performance</figcaption>
</figure>

────────────────────────────────────
LISTS
────────────────────────────────────

HTML provides three types of lists: unordered, ordered, and description lists.

Unordered lists — <ul>:
Unordered lists display items with bullet points. The order of items does not matter semantically. Each item uses an <li> (list item) element.

<ul>
  <li>HTML</li>
  <li>CSS</li>
  <li>JavaScript</li>
</ul>

Ordered lists — <ol>:
Ordered lists display items with sequential numbers. The order matters — items are numbered automatically by the browser.

<ol>
  <li>Boil water</li>
  <li>Add pasta</li>
  <li>Cook for 10 minutes</li>
  <li>Drain and serve</li>
</ol>

The type attribute on ordered lists:
type controls the numbering style:
<ol type="1"> — default: 1, 2, 3...
<ol type="A"> — uppercase: A, B, C...
<ol type="a"> — lowercase: a, b, c...
<ol type="I"> — uppercase Roman: I, II, III...
<ol type="i"> — lowercase Roman: i, ii, iii...

The start attribute on ordered lists:
start sets the beginning number:
<ol start="5">
  <li>Fifth item</li>
  <li>Sixth item</li>
</ol>

Description lists — <dl>:
Description lists pair terms with their definitions or descriptions. They use three elements:
- <dl> — the description list container
- <dt> — the term
- <dd> — the description or definition

<dl>
  <dt>HTML</dt>
  <dd>HyperText Markup Language — the structure of web pages</dd>
  <dt>CSS</dt>
  <dd>Cascading Style Sheets — the styling of web pages</dd>
  <dt>JavaScript</dt>
  <dd>The programming language for web interactivity</dd>
</dl>

Nested lists:
Lists can be nested inside each other. A nested list goes inside an <li> element.

<ul>
  <li>Frontend
    <ul>
      <li>HTML</li>
      <li>CSS</li>
      <li>JavaScript</li>
    </ul>
  </li>
  <li>Backend
    <ul>
      <li>Python</li>
      <li>Node.js</li>
    </ul>
  </li>
</ul>

Lists in navigation:
Navigation menus on websites are almost always built using unordered lists, because a set of links has no inherent order. CSS then styles them horizontally or vertically.

<nav>
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/about">About</a></li>
    <li><a href="/contact">Contact</a></li>
  </ul>
</nav>
""",
    "examples": """
Example 1 — Basic image:
<img src="sunset.jpg" alt="A golden sunset over the ocean" width="600" height="400">
# Browser displays the image. If it fails to load, shows the alt text instead.

Example 2 — Image with figure and caption:
<figure>
  <img src="diagram.png" alt="System architecture diagram" width="800" height="500">
  <figcaption>Figure 1: Overview of the system architecture</figcaption>
</figure>
# Semantic grouping of image and caption.

Example 3 — Unordered list:
<h2>Skills</h2>
<ul>
  <li>Python</li>
  <li>SQL</li>
  <li>HTML and CSS</li>
  <li>Git</li>
</ul>
# Renders as a bulleted list. Order does not matter semantically.

Example 4 — Ordered list with custom start:
<h2>Steps to Deploy</h2>
<ol>
  <li>Run tests</li>
  <li>Build the project</li>
  <li>Push to staging</li>
  <li>Verify staging</li>
  <li>Deploy to production</li>
</ol>
# Renders: 1. Run tests  2. Build the project  ... (numbered in order)

Example 5 — Nested list:
<ul>
  <li>Web Technologies
    <ul>
      <li>HTML</li>
      <li>CSS</li>
    </ul>
  </li>
  <li>Programming Languages
    <ul>
      <li>Python</li>
      <li>JavaScript</li>
    </ul>
  </li>
</ul>

Example 6 — Navigation menu using list:
<nav>
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/portfolio">Portfolio</a></li>
    <li><a href="/blog">Blog</a></li>
    <li><a href="/contact">Contact</a></li>
  </ul>
</nav>
# Semantically correct nav menu. CSS would style this horizontally.

Example 7 — Description list:
<dl>
  <dt>Stack</dt>
  <dd>Last In First Out data structure</dd>
  <dt>Queue</dt>
  <dd>First In First Out data structure</dd>
</dl>
""",
    "key_points": """
- <img> is a void element — it has no closing tag
- src sets the image source path (relative or absolute URL)
- alt is required on every img element — describes the image for screen readers and fallback display
- width and height on img prevent layout shift during page load
- JPEG for photos, PNG for transparency, SVG for scalable icons, WebP for modern efficiency
- <figure> and <figcaption> semantically pair an image with its caption
- <ul> creates unordered (bulleted) lists — use when order does not matter
- <ol> creates ordered (numbered) lists — use when sequence matters
- <li> is the list item element used in both ul and ol
- <dl>, <dt>, <dd> create description lists for term-definition pairs
- ol supports type attribute (1, A, a, I, i) and start attribute for custom numbering
- Lists can be nested by placing a ul or ol inside an li element
- Navigation menus are semantically built with ul containing a elements
""",
    "misconceptions": """
- "alt is optional on images" — alt is required for accessibility and SEO. Omitting it breaks screen reader navigation and is an accessibility violation. Decorative images should use alt="" (empty, not absent).
- "img needs a closing tag" — img is a void element. Writing </img> is invalid HTML.
- "ul is only for bulleted lists and ol is only for numbered lists" — The semantic distinction is about meaning, not appearance. CSS can remove bullets from ul or add them to ol. Use ul when order is unimportant, ol when sequence matters.
- "width and height attributes are just for styling" — These attributes tell the browser how much space to reserve before the image loads, preventing layout shift. They are a performance and stability attribute, not just visual.
- "Description lists are rarely useful" — dl is highly appropriate for FAQs, glossaries, metadata pairs, and any term-value content. It is underused but semantically meaningful.
- "Nested lists are bad practice" — Nested lists are correct and common for hierarchical content like outlines, menus, and category trees. Improper nesting (list outside li) is the actual problem to avoid.
""",
    "real_world_use": """
- Product pages on e-commerce sites use img with alt text for product photos and accessibility compliance
- Technical documentation uses figure and figcaption to label diagrams and screenshots
- Navigation menus on virtually every website are built with ul and li containing anchor links
- Recipe websites use ordered lists for step-by-step cooking instructions
- Feature comparison pages use unordered lists for bullet-pointed benefits and specifications
- Glossary pages and API documentation use description lists to pair terms with definitions
""",
    "next_concept_link": """
Images and lists cover two major content types in HTML. The next concept — Forms and Inputs — introduces interactive HTML: how to collect data from users through text fields, checkboxes, radio buttons, dropdowns, and submit buttons, which are the foundation of login pages, search bars, and every web form you have ever filled out.
"""
})

# ─────────────────────────────────────────────
# H5: Forms and Inputs
# ─────────────────────────────────────────────
concepts.append({
    "concept_id": "H5",
    "topic": "Forms and Inputs",
    "base_content": """
Forms are how users send data to a web server. Every login page, search bar, registration form, checkout page, and contact form is built with HTML form elements. Forms collect user input and submit it to a server for processing.

The <form> element:
The form element wraps all input fields and controls. It has two key attributes:
- action — the URL where the form data is sent on submission
- method — the HTTP method used to send data (GET or POST)

<form action="/submit" method="POST">
  <!-- inputs go here -->
</form>

GET vs POST:
GET appends form data to the URL as query parameters. Suitable for search forms and filtering. Data is visible in the URL.
POST sends form data in the HTTP request body. Suitable for sensitive data like passwords, large data, or creating/updating records. Data is not visible in the URL.

The <input> element:
input is the most versatile form element. The type attribute controls what kind of input it creates.

Text input:
<input type="text" name="username" placeholder="Enter username">

Password input (text is hidden):
<input type="password" name="password" placeholder="Enter password">

Email input (validates email format on submission):
<input type="email" name="email" placeholder="user@example.com">

Number input:
<input type="number" name="age" min="0" max="120">

Date input:
<input type="date" name="birthday">

Checkbox (multiple selections allowed):
<input type="checkbox" name="terms" value="agreed"> I agree to terms

Radio buttons (only one selection allowed in a group — same name):
<input type="radio" name="gender" value="male"> Male
<input type="radio" name="gender" value="female"> Female

Range slider:
<input type="range" name="rating" min="1" max="10" value="5">

File upload:
<input type="file" name="resume">

Hidden input (data sent with form but not shown to user):
<input type="hidden" name="form_token" value="abc123">

Submit button:
<input type="submit" value="Send">

The <label> element:
Labels associate text with an input, improving usability and accessibility. Clicking the label focuses or activates its associated input. The for attribute must match the input's id.

<label for="username">Username:</label>
<input type="text" id="username" name="username">

The <textarea> element:
textarea creates a multi-line text input. Unlike input, it has a closing tag. rows and cols set the default visible size.
<label for="message">Message:</label>
<textarea id="message" name="message" rows="5" cols="40" placeholder="Write your message..."></textarea>

The <select> element:
select creates a dropdown menu. Each option is an <option> element. The selected attribute pre-selects an option.
<label for="country">Country:</label>
<select id="country" name="country">
  <option value="in">India</option>
  <option value="us">United States</option>
  <option value="uk" selected>United Kingdom</option>
</select>

Grouping options with <optgroup>:
<select name="language">
  <optgroup label="Frontend">
    <option value="html">HTML</option>
    <option value="css">CSS</option>
  </optgroup>
  <optgroup label="Backend">
    <option value="python">Python</option>
    <option value="node">Node.js</option>
  </optgroup>
</select>

The <button> element:
button is more flexible than input type="submit". It can contain HTML content and is preferred for styled buttons.
<button type="submit">Submit Form</button>
<button type="reset">Clear Form</button>
<button type="button" onclick="doSomething()">Click Me</button>

Form validation attributes:
HTML5 provides built-in client-side validation without JavaScript:
- required — field must not be empty
- minlength / maxlength — minimum/maximum character count
- min / max — minimum/maximum value for numbers and dates
- pattern — regex pattern the value must match
- type="email" / type="url" — validates format automatically

<input type="text" name="username" required minlength="3" maxlength="20">
<input type="email" name="email" required>
<input type="text" name="zipcode" pattern="[0-9]{6}" title="6-digit zip code">

The name attribute:
name is critical. When the form is submitted, data is sent as name=value pairs. Without name, the input value is not included in the submission.

Fieldsets and legends:
fieldset groups related inputs visually and semantically. legend provides a label for the group.
<fieldset>
  <legend>Personal Information</legend>
  <label for="fname">First Name:</label>
  <input type="text" id="fname" name="fname">
  <label for="lname">Last Name:</label>
  <input type="text" id="lname" name="lname">
</fieldset>

Complete login form example:
<form action="/login" method="POST">
  <label for="email">Email:</label>
  <input type="email" id="email" name="email" required>
  <label for="password">Password:</label>
  <input type="password" id="password" name="password" required minlength="8">
  <button type="submit">Log In</button>
</form>
""",
    "examples": """
Example 1 — Simple contact form:
<form action="/contact" method="POST">
  <label for="name">Name:</label>
  <input type="text" id="name" name="name" required>

  <label for="email">Email:</label>
  <input type="email" id="email" name="email" required>

  <label for="message">Message:</label>
  <textarea id="message" name="message" rows="5" required></textarea>

  <button type="submit">Send Message</button>
</form>

Example 2 — Registration form with validation:
<form action="/register" method="POST">
  <label for="username">Username:</label>
  <input type="text" id="username" name="username" required minlength="3" maxlength="20">

  <label for="email">Email:</label>
  <input type="email" id="email" name="email" required>

  <label for="password">Password:</label>
  <input type="password" id="password" name="password" required minlength="8">

  <label for="age">Age:</label>
  <input type="number" id="age" name="age" min="13" max="120" required>

  <button type="submit">Create Account</button>
</form>

Example 3 — Radio buttons and checkboxes:
<form>
  <p>Choose your role:</p>
  <input type="radio" id="student" name="role" value="student">
  <label for="student">Student</label>
  <input type="radio" id="teacher" name="role" value="teacher">
  <label for="teacher">Teacher</label>

  <p>Select topics:</p>
  <input type="checkbox" id="python" name="topics" value="python">
  <label for="python">Python</label>
  <input type="checkbox" id="sql" name="topics" value="sql">
  <label for="sql">SQL</label>
</form>

Example 4 — Dropdown select:
<form action="/search" method="GET">
  <label for="category">Category:</label>
  <select id="category" name="category">
    <option value="">-- Select --</option>
    <option value="books">Books</option>
    <option value="electronics">Electronics</option>
    <option value="clothing">Clothing</option>
  </select>
  <button type="submit">Search</button>
</form>

Example 5 — Fieldset grouping:
<form action="/profile" method="POST">
  <fieldset>
    <legend>Personal Information</legend>
    <label for="fname">First Name:</label>
    <input type="text" id="fname" name="fname" required>
    <label for="lname">Last Name:</label>
    <input type="text" id="lname" name="lname" required>
  </fieldset>
  <fieldset>
    <legend>Account Details</legend>
    <label for="email">Email:</label>
    <input type="email" id="email" name="email" required>
    <label for="password">Password:</label>
    <input type="password" id="password" name="password" required>
  </fieldset>
  <button type="submit">Save Profile</button>
</form>
""",
    "key_points": """
- <form> wraps all input elements; action sets destination URL; method sets GET or POST
- GET sends data in the URL (visible); POST sends data in the request body (hidden)
- <input type="..."> is the core element — type controls the input behavior
- Common input types: text, password, email, number, date, checkbox, radio, file, hidden, submit
- <label> improves accessibility — for attribute must match input id
- Radio buttons sharing the same name attribute form a group — only one can be selected
- Checkboxes with the same name allow multiple selections
- <textarea> creates multi-line text input with rows and cols for default size
- <select> creates a dropdown; <option> defines each choice; selected pre-selects
- <button type="submit"> is the preferred way to submit forms
- name attribute is required for data to be included in form submission
- HTML5 validation attributes: required, minlength, maxlength, min, max, pattern
- <fieldset> and <legend> group related inputs semantically
""",
    "misconceptions": """
- "GET and POST are just preferences" — They have fundamentally different behaviors. GET data appears in the URL and is bookmarkable and cached. POST data is in the request body, appropriate for passwords and data changes. Sending passwords via GET exposes them in browser history and server logs.
- "label is just decorative text before an input" — label is an accessibility element. Using for/id linking means clicking the label focuses the input. Screen readers announce the label when the input is focused. Using label only as visual text breaks this.
- "input type='text' works for everything" — Specialized types like email, number, date, and tel provide built-in validation, appropriate mobile keyboards, and browser UI improvements. Using text for everything forfeits these benefits.
- "required is enough for security" — HTML validation runs in the browser and can be bypassed easily by disabling JavaScript or manipulating requests. Always validate on the server as well.
- "name and id are the same" — id uniquely identifies an element for CSS and JavaScript. name is used for form submission and server-side data processing. They serve different purposes, though they often share the same value for label association.
- "button and input type='submit' are identical" — button is more flexible. It can contain HTML like icons and styled text. input type='submit' only accepts plain text in value. button is preferred in modern HTML.
""",
    "real_world_use": """
- Login and registration pages on every website use forms with email, password inputs and POST method
- Search bars like Google use forms with GET method so searches are bookmarkable via URL
- E-commerce checkout flows use forms with fieldsets grouping shipping, billing, and payment sections
- File upload features (profile pictures, document uploads) use input type='file' inside forms
- Survey tools and quizzes use radio buttons and checkboxes for single and multiple choice answers
- Contact forms on websites collect name, email, and message via POST and send to email APIs
""",
    "next_concept_link": """
Forms and Inputs establish how users interact with web pages through data entry. The next concept — Web Accessibility — ensures that all users, including those with disabilities, can perceive, navigate, and interact with web content. Accessibility builds directly on proper use of semantic HTML, labels, headings, and attributes that have been introduced in previous concepts.
"""
})

# ─────────────────────────────────────────────
# H6: Web Accessibility
# ─────────────────────────────────────────────
concepts.append({
    "concept_id": "H6",
    "topic": "Web Accessibility",
    "base_content": """
Web accessibility means designing and building websites so that people with disabilities can perceive, understand, navigate, and interact with them. Accessibility is not a feature — it is a fundamental requirement of good web development.

Why accessibility matters:
- Approximately 15% of the global population lives with some form of disability
- Disabilities include visual, auditory, motor, cognitive, and speech impairments
- Legal requirements in many countries mandate web accessibility (ADA in the US, EN 301 549 in Europe)
- Accessible sites are better for all users — good contrast, clear structure, and keyboard navigation benefit everyone
- Search engines benefit from the same semantic clarity that accessibility requires

WCAG — Web Content Accessibility Guidelines:
WCAG is the international standard for web accessibility, published by the W3C. It organizes requirements around four principles — POUR:
- Perceivable — content can be perceived by all senses
- Operable — interface can be operated by keyboard and other input devices
- Understandable — content and operation are clear and predictable
- Robust — content works with assistive technologies including screen readers

WCAG has three conformance levels: A (minimum), AA (standard), AAA (enhanced). Most legal requirements target AA.

Semantic HTML is the foundation of accessibility:
Using the correct HTML element for its intended purpose provides built-in accessibility. Screen readers interpret semantic tags to understand page structure.
- Use <h1>–<h6> for headings, not styled divs
- Use <button> for buttons, not styled divs or spans
- Use <nav> for navigation, <main> for main content, <footer> for footer
- Use <ul> or <ol> for lists, not paragraphs with dashes
- Use <table> for tabular data, not for layout

Landmark elements — semantic page structure:
HTML5 landmark elements define major page regions, enabling screen reader users to jump directly to sections:
<header>   — page or section header
<nav>      — navigation links
<main>     — primary content (only one per page)
<aside>    — supplementary content (sidebar)
<footer>   — page or section footer
<section>  — thematic grouping of content
<article>  — self-contained, distributable content

<header>
  <nav>...</nav>
</header>
<main>
  <article>
    <h1>Article Title</h1>
    <section>...</section>
  </article>
  <aside>Related links</aside>
</main>
<footer>...</footer>

Alternative text for images:
Every informational image must have a descriptive alt attribute. Screen readers read the alt text aloud.
<img src="chart.png" alt="Bar chart showing sales rising 30% in Q3">

Decorative images (purely visual, no information) should have empty alt so screen readers skip them:
<img src="decorative-border.png" alt="">

ARIA — Accessible Rich Internet Applications:
ARIA attributes extend native HTML semantics for complex interactive widgets that HTML alone cannot describe. Use ARIA only when native HTML elements cannot achieve the required semantics.

Key ARIA attributes:
- role — defines what an element is (e.g., role="dialog", role="alert", role="tab")
- aria-label — provides an accessible name when visible text is not available
- aria-labelledby — points to the id of an element that labels this element
- aria-describedby — points to an element that describes this element
- aria-hidden="true" — hides element from screen readers (decorative icons)
- aria-expanded — indicates if a collapsible element is open or closed
- aria-required="true" — indicates a form field is required
- aria-live — announces dynamic content updates to screen readers

<!-- Icon button with no visible text -->
<button aria-label="Close dialog">
  <svg aria-hidden="true">...</svg>
</button>

<!-- Alert announced immediately by screen readers -->
<div role="alert" aria-live="assertive">
  Form submitted successfully.
</div>

Keyboard accessibility:
All interactive elements must be operable by keyboard alone (no mouse required). Native HTML elements handle this automatically:
- <a>, <button>, <input>, <select>, <textarea> are focusable by default
- Tab navigates forward through focusable elements
- Shift+Tab navigates backward
- Enter activates links and buttons
- Space activates checkboxes and buttons

tabindex attribute:
tabindex="0" — makes a non-interactive element focusable in the natural tab order
tabindex="-1" — removes element from tab order but allows programmatic focus
tabindex="1+" — creates a custom tab order (avoid — creates confusing navigation)

<!-- Making a custom widget keyboard focusable -->
<div role="button" tabindex="0" aria-label="Toggle menu">☰</div>

Color and contrast:
WCAG AA requires a contrast ratio of at least 4.5:1 for normal text and 3:1 for large text. Low contrast text is unreadable for users with low vision or color blindness.

Focus indicators:
Do not remove the visible focus outline with CSS (outline: none). Users navigating by keyboard rely on it to see which element is active.
/* Correct — enhance, never remove focus */
:focus {
  outline: 3px solid #0066cc;
  outline-offset: 2px;
}

Form accessibility:
- Always associate labels with inputs using for and id
- Use fieldset and legend to group related inputs
- Show error messages inline near the field, not only by color
- Provide aria-describedby to link input to its error message

<label for="email">Email address:</label>
<input type="email" id="email" aria-describedby="email-error" required>
<span id="email-error" role="alert">Please enter a valid email address.</span>

Accessible tables:
Use <th> for header cells. Use scope attribute to identify if header is for a row or column. Use <caption> for table title.
<table>
  <caption>Monthly Sales Report</caption>
  <tr>
    <th scope="col">Month</th>
    <th scope="col">Sales</th>
  </tr>
  <tr>
    <td>January</td>
    <td>₹50,000</td>
  </tr>
</table>

Skip navigation links:
Screen reader users and keyboard users must tab through all navigation links before reaching main content on every page load. A skip link allows them to jump directly to the main content.
<a href="#main-content" class="skip-link">Skip to main content</a>
...
<main id="main-content">...</main>

The skip link is usually visually hidden but becomes visible on focus for keyboard users.
""",
    "examples": """
Example 1 — Semantic landmark structure:
<body>
  <header>
    <h1>My Website</h1>
    <nav aria-label="Main navigation">
      <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
      </ul>
    </nav>
  </header>
  <main>
    <article>
      <h2>Latest Article</h2>
      <p>Content here.</p>
    </article>
  </main>
  <footer>
    <p>© 2025 My Website</p>
  </footer>
</body>

Example 2 — Accessible image:
<!-- Informational image -->
<img src="revenue-chart.png" alt="Line chart showing revenue growth from ₹10L in January to ₹18L in June">

<!-- Decorative image -->
<img src="divider.png" alt="">

Example 3 — Accessible form with error:
<form>
  <label for="username">Username:</label>
  <input type="text" id="username" name="username"
         aria-describedby="username-hint username-error" required>
  <span id="username-hint">3–20 characters, letters and numbers only</span>
  <span id="username-error" role="alert">Username is already taken</span>
</form>

Example 4 — ARIA for custom widget:
<!-- Toggle button with aria-expanded -->
<button aria-expanded="false" aria-controls="menu" id="menu-btn">
  Menu
</button>
<ul id="menu" hidden>
  <li><a href="/">Home</a></li>
  <li><a href="/about">About</a></li>
</ul>

Example 5 — Accessible table:
<table>
  <caption>Student Scores</caption>
  <thead>
    <tr>
      <th scope="col">Name</th>
      <th scope="col">Score</th>
      <th scope="col">Grade</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Arjun</td>
      <td>92</td>
      <td>A</td>
    </tr>
  </tbody>
</table>

Example 6 — Skip navigation link:
<a href="#main" style="position:absolute; left:-9999px; top:auto;">
  Skip to main content
</a>
<nav>...</nav>
<main id="main">
  <h1>Page Content</h1>
</main>
""",
    "key_points": """
- Accessibility ensures all users, including those with disabilities, can use web content
- WCAG (Web Content Accessibility Guidelines) defines the international standard — four principles: Perceivable, Operable, Understandable, Robust
- Semantic HTML is the foundation — use correct elements for their intended purpose
- Landmark elements (header, nav, main, aside, footer) define major page regions for screen readers
- All informational images require descriptive alt text; decorative images use alt=""
- ARIA attributes extend HTML semantics — use only when native HTML is insufficient
- All interactive elements must be keyboard accessible — never remove default keyboard behavior
- tabindex="0" makes custom elements focusable; tabindex="-1" removes from tab order
- Color contrast ratio must be at least 4.5:1 for normal text (WCAG AA)
- Never remove focus outlines — keyboard users depend on them for navigation
- Always associate labels with form inputs using for and id
- Show form errors near the field with role="alert" — not only through color
- Use th with scope and caption for accessible tables
- Skip navigation links let keyboard users jump past repeated navigation
""",
    "misconceptions": """
- "Accessibility is only for blind users" — Accessibility covers visual, auditory, motor, and cognitive disabilities. It also benefits elderly users, users in difficult environments (bright sunlight, noisy rooms), and users on slow connections.
- "ARIA fixes inaccessible HTML" — ARIA adds roles and labels but cannot fix poor semantic structure. An ARIA role on a div does not give it the keyboard behavior of a native button. Fix the HTML first; use ARIA only to supplement.
- "If it looks good visually, it is accessible" — Visual design and accessibility are different concerns. Color contrast, keyboard navigation, screen reader announcements, and focus management are invisible to sighted mouse users but critical for others.
- "alt='image' or alt='photo' is good enough" — The alt text must describe what the image communicates. alt='image' provides no information. alt='Bar chart showing 40% increase in Q3 revenue' is meaningful.
- "Accessibility is expensive to add later" — Accessibility is far cheaper when built from the start using semantic HTML. Retrofitting an inaccessible site is significantly more costly than getting it right initially.
- "tabindex with positive values improves navigation" — Positive tabindex values (1, 2, 3...) create a custom tab order that conflicts with the visual layout, confusing users. Use tabindex="0" and rely on natural DOM order instead.
""",
    "real_world_use": """
- Government and public sector websites are legally required to meet WCAG AA accessibility standards in most countries
- Major tech companies (Google, Microsoft, Apple) publish accessibility standards and audit their products against WCAG
- Screen readers like NVDA, JAWS, and VoiceOver interpret HTML semantics and ARIA to narrate page content to blind users
- Keyboard-only navigation is essential for users with motor disabilities who cannot use a mouse
- Automated accessibility testing tools (axe, Lighthouse, WAVE) scan HTML for WCAG violations
- Subtitles and transcripts on video platforms (YouTube, Netflix) serve deaf and hard-of-hearing users
""",
    "next_concept_link": """
Web Accessibility establishes the standards and techniques for building inclusive web experiences. The next concept — Service Workers — moves beyond static page rendering into the offline and background processing capabilities of the modern web, enabling Progressive Web Apps that work without a network connection and load instantly on repeat visits.
"""
})

# ─────────────────────────────────────────────
# H7: Service Workers
# ─────────────────────────────────────────────
concepts.append({
    "concept_id": "H7",
    "topic": "Service Workers",
    "base_content": """
A service worker is a JavaScript file that runs in the background, separate from the main web page, in its own thread. It acts as a programmable network proxy between the browser and the network. Service workers enable web applications to work offline, load instantly, and deliver features that previously required native mobile apps.

Service workers are the foundation of Progressive Web Apps (PWAs) — web applications that behave like native apps on mobile and desktop.

What service workers can do:
- Intercept and respond to network requests (cache responses, serve offline content)
- Cache assets and API responses for offline use
- Enable background sync (retry failed requests when connection is restored)
- Receive push notifications even when the browser is closed
- Pre-fetch resources in the background

What service workers cannot do:
- Access the DOM directly (they run in a separate thread)
- Use synchronous APIs (only async/Promise-based APIs)
- Run continuously — they are event-driven and started by the browser as needed

Service worker lifecycle:
1. Registration — the page registers the service worker file
2. Installation — browser downloads and installs the service worker; assets are cached
3. Activation — old service workers are replaced; the new one takes control
4. Idle — service worker sleeps until an event fires (fetch, push, sync)
5. Terminated — browser may terminate idle service workers to save resources

Registering a service worker:
Registration happens from the main page JavaScript. The register() call tells the browser where the service worker file is.

// In main JavaScript file (app.js or index.html script)
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js')
    .then(registration => {
      console.log('Service Worker registered:', registration.scope);
    })
    .catch(error => {
      console.log('Registration failed:', error);
    });
}

The feature check ('serviceWorker' in navigator) ensures the code runs only in browsers that support service workers.

The service worker file (sw.js):
The service worker listens for lifecycle events: install, activate, and fetch.

Install event — cache static assets:
const CACHE_NAME = 'my-app-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/offline.html'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('Caching assets');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

Activate event — clean old caches:
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME)
            .map(key => caches.delete(key))
      );
    })
  );
});

Fetch event — intercept network requests:
The fetch event fires for every network request made by the page. The service worker can serve the cached response, fall through to the network, or combine both.

Cache-first strategy (serve from cache, fall back to network):
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      if (cachedResponse) {
        return cachedResponse;  // Serve from cache
      }
      return fetch(event.request);  // Fall back to network
    })
  );
});

Network-first strategy (try network, fall back to cache):
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});

Offline fallback strategy:
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match('/offline.html');
    })
  );
});

Caching strategies:
- Cache-first — fast for static assets. Risk: stale content.
- Network-first — always fresh content. Risk: slow on poor connection.
- Cache-then-network — show cached content immediately, update in background (stale-while-revalidate).
- Network-only — no caching. Standard requests.
- Cache-only — serve from cache always. Used for fully offline apps.

Background sync:
Background sync allows the app to defer actions until the user has a stable internet connection. For example, a message composed offline is sent when connectivity is restored.

// In main page
navigator.serviceWorker.ready.then(registration => {
  return registration.sync.register('send-message');
});

// In service worker
self.addEventListener('sync', event => {
  if (event.tag === 'send-message') {
    event.waitUntil(sendPendingMessages());
  }
});

Push notifications:
Service workers can receive push messages from a server and display notifications even when the page is closed.

self.addEventListener('push', event => {
  const data = event.data.json();
  self.registration.showNotification(data.title, {
    body: data.body,
    icon: '/icon.png'
  });
});

Security requirements:
Service workers only work over HTTPS (or localhost for development). This is enforced because a service worker can intercept all network requests — it must be served securely to prevent man-in-the-middle attacks.

Browser support:
Service workers are supported in all modern browsers (Chrome, Firefox, Safari, Edge). They are not available in Internet Explorer.

Updating a service worker:
When sw.js changes, the browser detects it and installs the new version. The new service worker waits until all tabs using the old version are closed, then activates. Calling self.skipWaiting() in the install event and clients.claim() in the activate event forces immediate activation.
self.addEventListener('install', event => {
  self.skipWaiting();
  // ... cache assets
});
self.addEventListener('activate', event => {
  clients.claim();
  // ... clean old caches
});
""",
    "examples": """
Example 1 — Register a service worker from the main page:
// app.js
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => console.log('SW registered for scope:', reg.scope))
      .catch(err => console.error('SW registration failed:', err));
  });
}

Example 2 — Complete service worker with install, activate, fetch:
// sw.js
const CACHE = 'app-cache-v1';
const FILES = ['/', '/index.html', '/style.css', '/app.js', '/offline.html'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(FILES))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  clients.claim();
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(cached => cached || fetch(event.request))
      .catch(() => caches.match('/offline.html'))
  );
});

Example 3 — Network-first with cache fallback:
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Also update cache with fresh response
        const clone = response.clone();
        caches.open(CACHE).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

Example 4 — Push notification:
// sw.js
self.addEventListener('push', event => {
  const payload = event.data ? event.data.json() : { title: 'Update', body: 'New content available' };
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: '/icons/icon-192.png',
      badge: '/icons/badge.png'
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
""",
    "key_points": """
- A service worker is a JavaScript background thread separate from the main page
- It acts as a programmable network proxy — it can intercept, cache, and respond to requests
- Service workers enable offline functionality, fast loading, and push notifications
- They are the core technology of Progressive Web Apps (PWAs)
- Lifecycle: registration → installation → activation → idle → terminated
- The install event is used to pre-cache static assets
- The activate event is used to delete outdated caches
- The fetch event intercepts every network request made by the page
- Caching strategies: cache-first, network-first, cache-then-network, offline fallback
- Service workers only work over HTTPS (or localhost for development)
- Service workers cannot access the DOM — they communicate via the postMessage API
- skipWaiting() and clients.claim() force immediate activation of updated service workers
- Background sync retries failed requests when connectivity is restored
- Push notifications work even when the browser tab is closed
""",
    "misconceptions": """
- "Service workers are just regular JavaScript files" — Service workers run in a separate thread with no access to the DOM or window object. They use a different API surface (self, caches, fetch events) and are event-driven, not continuous.
- "Service workers work on HTTP" — Service workers require HTTPS. This is a hard browser requirement because a service worker can intercept all requests. The only exception is localhost, which is allowed for development.
- "Caching everything solves all performance problems" — Incorrect caching causes stale content, broken updates, and wasted storage. Choosing the right caching strategy for each resource type is critical.
- "Service workers replace server-side caching" — Service workers cache on the client (browser). Server-side caching (CDN, Redis) reduces load on the origin server. They solve different problems and are used together.
- "You need a service worker for every website" — Service workers add complexity. They are most valuable for apps that need offline capability, repeat visits, or push notifications. A simple static informational page does not need one.
- "Updating a service worker is instant" — The new service worker waits until all open tabs using the old version are closed before activating, unless skipWaiting() is used.
""",
    "real_world_use": """
- Twitter Lite and Pinterest use service workers to make their PWAs work offline and load instantly on repeat visits
- Google Maps PWA caches map tiles for recently viewed areas to enable partial offline navigation
- Starbucks web app uses service workers so customers can browse the menu and build an order while offline
- Push notification systems (news apps, messaging apps) use service workers to deliver notifications when the browser is closed
- News websites pre-cache articles in the background so they load instantly when clicked
- E-commerce apps use background sync to save cart additions made offline and sync them when connection returns
""",
    "next_concept_link": """
Service Workers enable the network and background capabilities of modern web apps. The final concept — Web Components — takes a different direction: instead of network-level programming, Web Components introduce a native browser standard for creating reusable, encapsulated custom HTML elements that work without any framework, forming the foundation of truly portable and maintainable UI architecture.
"""
})

# ─────────────────────────────────────────────
# H8: Web Components
# ─────────────────────────────────────────────
concepts.append({
    "concept_id": "H8",
    "topic": "Web Components",
    "base_content": """
Web Components are a set of native browser APIs that allow you to create reusable, self-contained custom HTML elements. They encapsulate their own structure (HTML), styling (CSS), and behavior (JavaScript) so they can be used in any web page or application without conflicting with the rest of the page.

Web Components are not a single technology — they are a suite of four interrelated browser standards that work together.

The four pillars of Web Components:
1. Custom Elements — define new HTML tags
2. Shadow DOM — encapsulate DOM and styles
3. HTML Templates — define inert, reusable HTML markup
4. ES Modules — import and export JavaScript components

────────────────────────────────────
1. CUSTOM ELEMENTS
────────────────────────────────────
Custom Elements allow you to define new HTML tags with custom behavior. There are two types:
- Autonomous custom elements — entirely new elements extending HTMLElement
- Customized built-in elements — extending existing elements like <button> or <input>

Defining a custom element:
class MyCard extends HTMLElement {
  constructor() {
    super();  // Always call super() first
    this.innerHTML = `<div class="card"><slot></slot></div>`;
  }
}

// Register the element — name must contain a hyphen
customElements.define('my-card', MyCard);

Using the custom element in HTML:
<my-card>
  <h2>Hello from My Card</h2>
  <p>This is content inside the card.</p>
</my-card>

Custom element naming rules:
Custom element names must contain at least one hyphen (-). This prevents conflicts with existing or future standard HTML elements (which never contain hyphens).
my-card ✓     user-profile ✓     search-bar ✓
mycard ✗      card ✗

Custom element lifecycle callbacks:
Custom elements have lifecycle callbacks that fire at different stages:
- connectedCallback() — called when element is added to the DOM
- disconnectedCallback() — called when element is removed from the DOM
- attributeChangedCallback(name, oldValue, newValue) — called when a watched attribute changes
- adoptedCallback() — called when element is moved to a new document

class MyTimer extends HTMLElement {
  connectedCallback() {
    this.start();
    console.log('Timer added to page');
  }

  disconnectedCallback() {
    this.stop();
    console.log('Timer removed from page');
  }

  static get observedAttributes() {
    return ['duration'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === 'duration') {
      this.duration = parseInt(newValue);
    }
  }
}

customElements.define('my-timer', MyTimer);

────────────────────────────────────
2. SHADOW DOM
────────────────────────────────────
Shadow DOM attaches a hidden, encapsulated DOM tree to an element. Styles and scripts inside the Shadow DOM do not leak out to the main page, and external styles do not leak in.

This solves a major problem in web development: CSS leaking between components. In a Shadow DOM, you can write h1 { color: red } and it only affects h1 inside that shadow tree, not every h1 on the page.

Creating a Shadow DOM:
class MyCard extends HTMLElement {
  constructor() {
    super();
    const shadow = this.attachShadow({ mode: 'open' });
    shadow.innerHTML = `
      <style>
        .card {
          border: 1px solid #ccc;
          padding: 16px;
          border-radius: 8px;
          font-family: Arial, sans-serif;
        }
      </style>
      <div class="card">
        <slot></slot>
      </div>
    `;
  }
}
customElements.define('my-card', MyCard);

mode: 'open' allows external JavaScript to access the shadow root via element.shadowRoot.
mode: 'closed' prevents external access to the shadow DOM.

Shadow DOM terminology:
- Shadow host — the regular DOM element that the shadow DOM is attached to
- Shadow root — the root of the shadow DOM tree
- Shadow tree — the DOM tree inside the shadow root
- Shadow boundary — the boundary between the regular DOM and the shadow DOM
- Slot — a placeholder inside the shadow DOM where the user's content is placed

────────────────────────────────────
3. HTML TEMPLATES
────────────────────────────────────
The <template> element holds HTML markup that is not rendered when the page loads. It is inert — scripts inside do not execute, images do not download. The template is activated by cloning it with JavaScript.

<template id="card-template">
  <style>
    .card { border: 1px solid #ccc; padding: 1rem; border-radius: 8px; }
    h2 { color: #333; }
  </style>
  <div class="card">
    <h2 class="title"></h2>
    <p class="description"></p>
  </div>
</template>

Using the template:
class MyCard extends HTMLElement {
  constructor() {
    super();
    const shadow = this.attachShadow({ mode: 'open' });
    const template = document.getElementById('card-template');
    const clone = template.content.cloneNode(true);  // deep clone
    shadow.appendChild(clone);
  }

  connectedCallback() {
    this.shadowRoot.querySelector('.title').textContent = this.getAttribute('title');
    this.shadowRoot.querySelector('.description').textContent = this.getAttribute('description');
  }
}
customElements.define('my-card', MyCard);

Using the component:
<my-card title="Web Components" description="Native browser components"></my-card>
<my-card title="Service Workers" description="Offline web capabilities"></my-card>

The <slot> element:
slot defines where the consumer's content goes inside the shadow DOM.

Default slot — accepts any content:
<slot></slot>

Named slots — place content in specific positions:
<!-- In shadow DOM template -->
<slot name="title"></slot>
<slot name="body"></slot>

<!-- In the HTML -->
<my-card>
  <h2 slot="title">Card Title</h2>
  <p slot="body">Card body content.</p>
</my-card>

────────────────────────────────────
4. ES MODULES
────────────────────────────────────
ES Modules allow component definitions to be organized in separate files and imported where needed. This makes Web Components modular, reusable, and maintainable.

// my-card.js
class MyCard extends HTMLElement { ... }
customElements.define('my-card', MyCard);
export default MyCard;

// In HTML
<script type="module" src="my-card.js"></script>
<my-card></my-card>

// Or as import in another module
import './my-card.js';

Styling Web Components from outside:
Even with Shadow DOM encapsulation, Web Components can expose styling hooks through CSS custom properties (variables). Variables defined outside penetrate the shadow boundary.

/* External stylesheet */
my-card {
  --card-bg: #f0f4ff;
  --card-border: 2px solid #0055cc;
}

/* Inside Shadow DOM */
.card {
  background: var(--card-bg, white);
  border: var(--card-border, 1px solid #ccc);
}

Web Components vs Frameworks:
Web Components are native browser standards — no build tools, no framework dependencies. They work in any framework (React, Vue, Angular) or in plain HTML. Frameworks like React and Vue offer more features (state management, virtual DOM), but Web Components provide true portability. Many design systems (Google's Material Web, Adobe Spectrum) are built with Web Components precisely because they work everywhere.
""",
    "examples": """
Example 1 — Minimal custom element:
class HelloWorld extends HTMLElement {
  connectedCallback() {
    this.textContent = 'Hello, World from a Web Component!';
  }
}
customElements.define('hello-world', HelloWorld);

// HTML
<hello-world></hello-world>
// Renders: Hello, World from a Web Component!

Example 2 — Custom element with Shadow DOM and styles:
class UserBadge extends HTMLElement {
  constructor() {
    super();
    const shadow = this.attachShadow({ mode: 'open' });
    shadow.innerHTML = `
      <style>
        .badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: #0055cc;
          color: white;
          padding: 6px 12px;
          border-radius: 20px;
          font-family: Arial, sans-serif;
          font-size: 14px;
        }
        .avatar {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: white;
          color: #0055cc;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
        }
      </style>
      <div class="badge">
        <div class="avatar" id="initial"></div>
        <span id="name"></span>
      </div>
    `;
  }

  connectedCallback() {
    const name = this.getAttribute('name') || 'User';
    this.shadowRoot.getElementById('name').textContent = name;
    this.shadowRoot.getElementById('initial').textContent = name[0].toUpperCase();
  }
}
customElements.define('user-badge', UserBadge);

// HTML usage
<user-badge name="Arjun"></user-badge>
<user-badge name="Priya"></user-badge>

Example 3 — Template with named slots:
<!-- In HTML file -->
<template id="product-card">
  <style>
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; max-width: 300px; }
    .price { color: green; font-size: 1.5rem; font-weight: bold; }
  </style>
  <div class="card">
    <slot name="title"><h3>Product</h3></slot>
    <slot name="price"><span class="price">₹0</span></slot>
    <slot name="description"><p>No description.</p></slot>
  </div>
</template>

<script>
class ProductCard extends HTMLElement {
  constructor() {
    super();
    const shadow = this.attachShadow({ mode: 'open' });
    const template = document.getElementById('product-card');
    shadow.appendChild(template.content.cloneNode(true));
  }
}
customElements.define('product-card', ProductCard);
</script>

<!-- Usage -->
<product-card>
  <h3 slot="title">Mechanical Keyboard</h3>
  <span slot="price">₹5,499</span>
  <p slot="description">Tactile switches, RGB backlight, compact 60% layout.</p>
</product-card>

Example 4 — Attribute change observation:
class CounterElement extends HTMLElement {
  static get observedAttributes() {
    return ['count'];
  }

  connectedCallback() {
    this.render();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    this.render();
  }

  render() {
    const count = parseInt(this.getAttribute('count') || '0');
    this.innerHTML = `<strong>Count: ${count}</strong>`;
  }
}
customElements.define('my-counter', CounterElement);

// HTML
<my-counter count="0"></my-counter>
// JavaScript: document.querySelector('my-counter').setAttribute('count', '5');
// Renders: Count: 5
""",
    "key_points": """
- Web Components are four native browser standards: Custom Elements, Shadow DOM, HTML Templates, ES Modules
- Custom Elements let you define new HTML tags by extending HTMLElement
- Custom element names must contain a hyphen to avoid conflicts with standard elements
- Lifecycle callbacks: connectedCallback, disconnectedCallback, attributeChangedCallback, adoptedCallback
- observedAttributes declares which attributes trigger attributeChangedCallback
- Shadow DOM attaches a private, encapsulated DOM and CSS scope to an element
- Shadow DOM prevents style leakage in both directions — inside to out, outside to in
- mode: 'open' allows JS access to shadowRoot; mode: 'closed' blocks it
- The <template> element holds inert markup that is only activated when cloned via JavaScript
- <slot> is a placeholder in shadow DOM where consumer-provided content is inserted
- Named slots (slot="name") allow placing content in specific positions in the shadow DOM
- CSS custom properties (variables) penetrate the shadow boundary for external theming
- ES Modules allow component definitions to live in separate, importable files
- Web Components work in any framework or plain HTML — they are framework-agnostic
""",
    "misconceptions": """
- "Web Components replace React or Vue" — Web Components and frameworks solve different problems. Web Components provide encapsulation and portability. Frameworks provide state management, reactivity, and tooling ecosystems. They are complementary — Web Components can be used inside React or Vue components.
- "Shadow DOM blocks all styling" — Shadow DOM blocks regular CSS selectors from penetrating. However, CSS custom properties (variables) and inherited properties (like font-family and color) do pass through. You can theme components from the outside using CSS variables.
- "Custom elements work without a hyphen in the name" — The hyphen is a hard browser requirement. Attempting to define 'card' or 'button' as a custom element will throw a DOMException. Always use a hyphen.
- "The template element renders hidden content" — The template element's content is completely inert. It is not in the DOM, scripts do not execute, and images do not load until the template is cloned and appended. It is not like display: none.
- "Web Components are too complex for small projects" — A basic custom element with connectedCallback and innerHTML is simpler than many JavaScript utilities. Complexity scales with features. Simple components are simple to write.
- "Closed Shadow DOM is more secure" — mode: 'closed' prevents external JavaScript from accessing shadowRoot through the standard API. However, it can still be bypassed. It is not a security boundary — it is an encapsulation signal.
""",
    "real_world_use": """
- Google's Material Web (formerly Material Design Components) is a complete UI library built entirely with Web Components
- Adobe Spectrum Web Components power the UI of Adobe's cloud applications
- GitHub uses custom elements throughout github.com for interactive UI components like dropdown menus and tooltips
- Salesforce Lightning Web Components are the core component technology for the Salesforce platform
- YouTube's video player interface uses custom elements for its player controls
- Design systems that need to work across multiple frameworks (React, Vue, Angular, plain HTML) are built with Web Components for true portability
""",
    "next_concept_link": """
Web Components complete the HTML and Web Basics curriculum by introducing native browser-level component architecture. From here, the knowledge path branches into deeper frontend development — CSS layout systems like Flexbox and Grid, JavaScript DOM manipulation, modern build tools, or framework-specific development with React or Vue — all of which build on the HTML foundation established across H1 through H8.
"""
})

# ─────────────────────────────────────────────
# Database Insertion
# ─────────────────────────────────────────────


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

create_concept_resources_table(cursor)

for concept in concepts:
    cursor.execute("""
        INSERT INTO concept_resources (
            concept_id,
            topic,
            base_content,
            examples,
            key_points,
            misconceptions,
            real_world_use,
            next_concept_link
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(concept_id) DO UPDATE SET
            topic             = excluded.topic,
            base_content      = excluded.base_content,
            examples          = excluded.examples,
            key_points        = excluded.key_points,
            misconceptions    = excluded.misconceptions,
            real_world_use    = excluded.real_world_use,
            next_concept_link = excluded.next_concept_link
    """, (
        concept["concept_id"],
        concept["topic"],
        concept["base_content"].strip(),
        concept["examples"].strip(),
        concept["key_points"].strip(),
        concept["misconceptions"].strip(),
        concept["real_world_use"].strip(),
        concept["next_concept_link"].strip()
    ))
    print(f"Success — concept '{concept['concept_id']}: {concept['topic']}' inserted or updated.")

conn.commit()
conn.close()

print("\nAll HTML concepts H1–H8 inserted successfully into html_web_basics.db")