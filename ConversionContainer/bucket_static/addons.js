let create_header = () => {
    let header = document.createElement('header');
    let ABS_URL_BASE = 'https://arxiv.org/abs';
    let id = window.location.pathname.split('/')[2];

    var LogoBanner = `
    <div style="display: flex; width: 60%;">
        <a href="https://arxiv.org/" style="text-decoration: none; width:80px">
            <img alt="logo" class="logo" role="presentation" style="background-color: transparent;" src="https://services.dev.arxiv.org/html/arxiv-logo-one-color-white.svg">
            <img alt="logo" class="logomark" role="presentation" style="background-color: transparent;" src="https://services.dev.arxiv.org/html/arxiv-logomark-small-white.svg">
        </a>
        <div class="header-message" role="banner" style="padding-left: 15px; padding-top: 5px;">
            ${id === 'submission' ? 'This is <strong>Experimental HTML</strong>. By design, HTML will not look exactly like the PDF. We invite you to report any errors that don\'t represent the intent or meaning of your paper. <span class="sr-only">Use Alt+Y to enable accessible section reporting links and Alt+Shift+Y to disable.</span>' :
                                  'This is <strong>Experimental HTML</strong>. We invite you to report rendering errors. <span class="sr-only">Use Alt+Y to toggle on accessible reporting links and Alt+Shift+Y to toggle off.</span>'}
        </div>
    </div>`;


    var Links = `
        <div style="display: inline-flex; align-items: center;">
            <a class="ar5iv-footer-button hover-effect" style="color: white;" href="#footer">Keyboard Commands</a>
            <a class="ar5iv-footer-button hover-effect" target="_blank" style="color: white;" href="#myForm" onclick="event.preventDefault(); var modal = document.getElementById('myForm'); modal.style.display = 'block'; bugReportState.setInitiateWay('Header');">Open Issue</a>
            <a class="ar5iv-footer-button hover-effect" style="color: white;" href="https://arxiv.org/abs/${window.location.href.match(/\/([^/]+)\.html/)[1]}">Back to Abstract</a>
            <a class="ar5iv-toggle-color-scheme" href="javascript:toggleColorScheme()" title="Toggle ar5iv color scheme" style="float: right;">
                <span class="color-scheme-icon"></span>
            </a>
        </div>`;

    header.innerHTML = LogoBanner + Links;
    document.body.insertBefore(header, document.body.firstChild);
};

let create_footer = () => {
    let footer = document.createElement('footer');
    let ltx_page_footer = document.createElement('div');
    ltx_page_footer.setAttribute('class', 'ltx_page_footer');
    footer.setAttribute('id', 'footer');
    footer.setAttribute('class', 'ltx_document');

    footer.innerHTML = `
        <div class="keyboard-glossary ltx_page_content">
            <h2>Keyboard commands and instructions for reporting errors</h2>
            <p>HTML versions of papers are experimental and a step towards improving accessibility and mobile device support. We appreciate feedback on errors in the HTML that will help us improve the conversion and rendering. Use the methods listed below to report errors:</p>
            <ul>
                <li>Use the "Open Issue" button.</li>
                <li>To open the report feedback form via keyboard, use "<strong>Ctrl + ?</strong>".</li>
                <li>You can make a text selection and use the "Open Issue for Selection" button that will display near your cursor.</li>
                <li class="sr-only">You can use Alt+Y to toggle on and Alt+Shift+Y to toggle off accessible reporting links at each section.</li>
            </ul>
            <p>We appreciate your time reviewing and reporting rendering errors in the HTML. It will help us improve the HTML versions for all readers and make papers more accessible, because disability should not be a barrier to accessing the research in your field.</p>
        </div>`;

    var night = `
        <a class="ar5iv-toggle-color-scheme" href="javascript:toggleColorScheme()" title="Toggle ar5iv color scheme">
            <span class="color-scheme-icon"></span>
        </a>`;

    var copyLink = `
        <a class="ar5iv-footer-button" href="https://arxiv.org/help/license" target="_blank">Copyright</a>`;

    var policyLink = `
        <a class="ar5iv-footer-button" href="https://arxiv.org/help/policies/privacy_policy" target="_blank">Privacy Policy</a>`;

    var HTMLLink = `
        <a class="ar5iv-footer-button" href="https://info.arxiv.org/about/accessible_HTML.html" target="_blank">Why HTML?</a>`;

    var TimeLogo = `
        <div class="ltx_page_logo">
            Generated on Wed Dec 14 18:01:44 2022 by
            <a href="https://math.nist.gov/~BMiller/LaTeXML/" class="ltx_LaTeXML_logo">
                <span style="letter-spacing: -0.2em; margin-right: 0.1em;">
                    L
                    <span style="font-size: 70%; position: relative; bottom: 2.2pt;">A</span>
                    T
                    <span style="position: relative; bottom: -0.4ex;">E</span>
                </span>
                <span class="ltx_font_smallcaps">xml</span>
                <img alt="[LOGO]" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAOCAYAAAD5YeaVAAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9wKExQZLWTEaOUAAAAddEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIFRoZSBHSU1Q72QlbgAAAdpJREFUKM9tkL+L2nAARz9fPZNCKFapUn8kyI0e4iRHSR1Kb8ng0lJw6FYHFwv2LwhOpcWxTjeUunYqOmqd6hEoRDhtDWdA8ApRYsSUCDHNt5ul13vz4w0vWCgUnnEc975arX6ORqN3VqtVZbfbTQC4uEHANM3jSqXymFI6yWazP2KxWAXAL9zCUa1Wy2tXVxheKA9YNoR8Pt+aTqe4FVVVvz05O6MBhqUIBGk8Hn8HAOVy+T+XLJfLS4ZhTiRJgqIoVBRFIoric47jPnmeB1mW/9rr9ZpSSn3Lsmir1fJZlqWlUonKsvwWwD8ymc/nXwVBeLjf7xEKhdBut9Hr9WgmkyGEkJwsy5eHG5vN5g0AKIoCAEgkEkin0wQAfN9/cXPdheu6P33fBwB4ngcAcByHJpPJl+fn54mD3Gg0NrquXxeLRQAAwzAYj8cwTZPwPH9/sVg8PXweDAauqqr2cDjEer1GJBLBZDJBs9mE4zjwfZ85lAGg2+06hmGgXq+j3+/DsixYlgVN03a9Xu8jgCNCyIegIAgx13Vfd7vdu+FweG8YRkjXdWy329+dTgeSJD3ieZ7RNO0VAXAPwDEAO5VKndi2fWrb9jWl9Esul6PZbDY9Go1OZ7PZ9z/lyuD3OozU2wAAAABJRU5ErkJggg==">
            </a>
        </div>`;

    footer.appendChild(ltx_page_footer);
    ltx_page_footer.innerHTML = night + copyLink + policyLink + HTMLLink + TimeLogo;
    ltx_page_footer.setAttribute('class', 'ltx_page_footer');

    document.body.appendChild(footer);
};

document.addEventListener("DOMContentLoaded", () => {
    create_header();
    create_footer();
});

document.addEventListener("DOMContentLoaded", function() {
    const referenceItems = document.querySelectorAll(".ltx_bibitem");
  
    referenceItems.forEach(item => {
      const referenceId = item.getAttribute("id");
      const backToReferenceBtn = document.createElement("button");
      backToReferenceBtn.innerHTML = "&#x2191;";
      backToReferenceBtn.classList.add("back-to-reference-btn");
  
      let scrollPosition = 0;
      let clickedCite = false;
  
      backToReferenceBtn.addEventListener("click", function() {
        if (clickedCite) {
          window.scrollTo(0, scrollPosition);
        } else {
          const citeElement = document.querySelector(`cite a[href="#${referenceId}"]`);
          if (citeElement) {
            citeElement.scrollIntoView({ behavior: "smooth" });
          }
        }
      });
  
      const citeElements = document.querySelectorAll(`cite a[href="#${referenceId}"]`);
      citeElements.forEach(citeElement => {
        citeElement.addEventListener("click", function() {
          scrollPosition = window.scrollY;
          clickedCite = true;
        });
      });
  
      const refNumElement = item.querySelector(".ltx_role_refnum");
      if (refNumElement) {
        refNumElement.appendChild(backToReferenceBtn);
      }
    });
  });

  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  


  