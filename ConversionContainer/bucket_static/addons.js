let create_header = () => {
    let header = document.createElement('header');
    let ABS_URL_BASE = 'https://arxiv.org/abs';
    let id = window.location.pathname.split('/')[2];
    if (id === 'submission') {
        header.innerHTML =
        '<a href="#main" class="skip">Skip to main content</a> \
        <img src="images/arxiv-logo-one-color-white.svg" alt="logo" role="presentation" class="logo"> \
        <img src="images/arxiv-logomark-small-white.svg" alt="logo" role="presentation" class="logomark"> \
        <div role="banner" class="header-message"> \
            <strong>Experimental HTML</strong>. Report rendering errors with the "Open Issue" button or click <strong>Shift+b</strong> to toggle accessible section reporting links. <a href="#footer">Reference all keyboard commands</a> in the footer. \
        </div> \
        <div></div>';
    } else {
        header.innerHTML =
        `<a href="#main" class="skip">Skip to main content</a> \
        <img src="images/arxiv-logo-one-color-white.svg" alt="logo" role="presentation" class="logo"> \
        <img src="images/arxiv-logomark-small-white.svg" alt="logo" role="presentation" class="logomark"> \
        <div role="banner" class="header-message"> \
            <strong>Experimental HTML</strong>. Report rendering errors with the "Open Issue" button or click <strong>Shift+b</strong> to toggle accessible section reporting links. <a href="#footer">Reference all keyboard commands</a> in the footer. \
        </div> \
        <a href="${ABS_URL_BASE}/${id}"> \
            Back to Abstract \
            <svg id="back-arrow" xmlns="http://www.w3.org/2000/svg" height="1em" viewBox="0 0 448 512"><path fill="#ffffff" d="M438.6 278.6c12.5-12.5 12.5-32.8 0-45.3l-160-160c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L338.8 224 32 224c-17.7 0-32 14.3-32 32s14.3 32 32 32l306.7 0L233.4 393.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l160-160z"/></svg> \
        </a>`;
    }

    document.body.insertBefore(header, document.body.firstChild);
}

let create_footer = () => {
    let footer = document.createElement('footer');
    footer.setAttribute('id', 'footer');
    footer.setAttribute('class', 'ltx_document');
    footer.innerHTML =
    '<div class="keyboard-glossary ltx_page_content"> \
        <h2>Keyboard commands and instructions for reporting errors</h2> \
        <p>HTML versions of papers are experimental and a step towards improving accessibility and mobile device support. We appreciate feedback on errors in the HTML that will help us improve the conversion and rendering. Use the methods listed below to report errors:</p> \
        <ul> \
            <li>Use the "Open Issue" button.</li> \
            <li><strong>Ctrl + ?</strong> will open the report feedback form via keyboard.</li> \
            <li>If using a screen reader, <strong>Shift + b</strong> will toggle individual reporting buttons at each section on and off. Useful when you want to report an issue just within a specific section, as highligting is not screen reader compatible.</li> \
            <li>You can also highlight any text and click the "Open Issue" button that will display near your cursor. Highlighting is not screen reader compatible so the method above is also available.</li> \
            <li>Reporting will prompt you to login to Github to complete the process. Need an account? <a href="https://github.com/account/organizations/new?plan=free" target="_blank">Create a GitHub account for free</a>.</li> \
        </ul> \
        <p>We appreciate your time reviewing and reporting rendering errors in the HTML. It will help us improve the HTML versions for all readers and make papers more accessible, because disability should not be a barrier to accessing the research in your field. <a href="https://info.arxiv.org/about/accessible_HTML.html" target="_blank">Why is it important that research papers be accessible?</a>.</p> \
    </div>';

    document.body.appendChild(footer);
}

document.addEventListener("DOMContentLoaded", () => {
    create_header();
    create_footer();
});