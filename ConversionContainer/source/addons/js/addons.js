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
            The HTML below is experimental. We invite you to report any rendering errors you find by clicking the "Report" button, or click <strong>Shift+b</strong> to toggle accessible reporting links at each section. <a href="#footer">Reference a list of keyboard commands</a> and instructions in the footer. \
        </div> \
        </a>';
    } else {
        header.innerHTML = 
        `<a href="#main" class="skip">Skip to main content</a> \
        <img src="images/arxiv-logo-one-color-white.svg" alt="logo" role="presentation" class="logo"> \
        <img src="images/arxiv-logomark-small-white.svg" alt="logo" role="presentation" class="logomark"> \
        <div role="banner" class="header-message"> \
            The HTML below is experimental. We invite you to report any rendering errors you find by clicking the "Report" button, or click <strong>Shift+b</strong> to toggle accessible reporting links at each section. <a href="#footer">Reference a list of keyboard commands</a> and instructions in the footer. \
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
        <h2>Keyboard commands and instructions for reporting</h2> \
        <p>Report rendering errors in the HTML by either clicking on the "Report" button or using the keyboard commands listed below</p> \
        <ul> \
            <li><strong>Shift + b</strong> will toggle individual reporting buttons at each section. Use these reporting buttons when you want to report an issue within a specific section.</li> \
            <li>[KEY COMMAND 2] will open a general report form. Use this to report an issue that applies to the paper overall.</li> \
            <li>Reporting will prompt you to login to your Github account. You can set up an account for free <a href="https://github.com/account/organizations/new?plan=free" target="_blank">here</a>.</li> \
        </ul> \
        <p>We appreciate your time reviewing and reporting rendering errors in the HTML. It will help us improve the HTML versions for all readers and make papers more accessible. <a href="https://info.arxiv.org/about/accessible_HTML.html" target="_blank">What is accessibility and why is it important?</a>.</p> \
    </div>';

    document.body.appendChild(footer);
}

document.addEventListener("DOMContentLoaded", () => {
    create_header();
    create_footer();
});