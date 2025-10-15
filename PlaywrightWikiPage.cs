using Microsoft.Playwright;
using System.Threading.Tasks;

namespace WikiTest.Infrastructure
{
    public class PlaywrightWikiPage
    {
        private readonly IPage _page;
        private const string Url = "https://en.wikipedia.org/wiki/Playwright_(software)";

        public PlaywrightWikiPage(IPage page)
        {
            _page = page;
        }

        public async Task GoToPageAsync()
        {
            await _page.GotoAsync(Url);
        }

        public async Task<string> GetDebuggingSectionTextAsync()
        {
            return await _page.Locator("h2:has-text('Debugging features') ~ p").First.TextContentAsync() ?? string.Empty;
        }

        public async Task<bool> AreTechLinksValidAsync()
        {
            var links = await _page.Locator("h3:has-text('Microsoft development tools') ~ ul li a").AllAsync();
            foreach (var link in links)
            {
                var href = await link.GetAttributeAsync("href");
                if (string.IsNullOrEmpty(href) || href == "#")
                    return false;
            }
            return true;
        }

        public async Task SwitchToDarkModeAsync()
        {
            await _page.Locator("a[title='Switch to dark mode']").ClickAsync();
        }

        public async Task<bool> IsDarkModeActiveAsync()
        {
            return await _page.Locator("html.mw-dark-mode").IsVisibleAsync();
        }
    }
}
