using WikiTest.Domain;
using Microsoft.Playwright;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;

namespace WikiTest.Infrastructure
{
    public class WikiPageService : IWikiPageService, IDisposable
    {
        private readonly IPlaywright _playwright;
        private readonly IBrowser _browser;
        private readonly HttpClient _httpClient;
        private bool _disposed;

        public WikiPageService()
        {
            _playwright = Playwright.CreateAsync().GetAwaiter().GetResult();
            _browser = _playwright.Chromium.LaunchAsync(new() { Headless = true }).GetAwaiter().GetResult();
            _httpClient = new HttpClient();
        }

        public async Task<string> GetDebuggingSectionTextAsync()
        {
            var page = await _browser.NewPageAsync();
            try
            {
                var wikiPage = new PlaywrightWikiPage(page);
                await wikiPage.GoToPageAsync();
                return await wikiPage.GetDebuggingSectionTextAsync();
            }
            finally
            {
                await page.CloseAsync();
            }
        }

        public async Task<WikiSection> GetSectionByTitleAsync(string title)
        {
            var response = await _httpClient.GetAsync($"https://en.wikipedia.org/w/api.php?action=parse&page=Playwright_(software)&prop=wikitext&sectiontitle={title}&format=json");
            response.EnsureSuccessStatusCode();
            var content = await response.Content.ReadAsStringAsync();
            using var jsonDoc = JsonDocument.Parse(content);
            var wikitext = jsonDoc.RootElement.GetProperty("parse").GetProperty("wikitext").GetProperty("*").GetString();
            return new WikiSection { Title = title, Content = wikitext ?? string.Empty };
        }

        public async Task<bool> AreTechLinksValidAsync()
        {
            var page = await _browser.NewPageAsync();
            try
            {
                var wikiPage = new PlaywrightWikiPage(page);
                await wikiPage.GoToPageAsync();
                return await wikiPage.AreTechLinksValidAsync();
            }
            finally
            {
                await page.CloseAsync();
            }
        }

        public async Task SwitchToDarkModeAsync()
        {
            var page = await _browser.NewPageAsync();
            try
            {
                var wikiPage = new PlaywrightWikiPage(page);
                await wikiPage.GoToPageAsync();
                await wikiPage.SwitchToDarkModeAsync();
            }
            finally
            {
                await page.CloseAsync();
            }
        }

        public async Task<bool> IsDarkModeActiveAsync()
        {
            var page = await _browser.NewPageAsync();
            try
            {
                var wikiPage = new PlaywrightWikiPage(page);
                await wikiPage.GoToPageAsync();
                return await wikiPage.IsDarkModeActiveAsync();
            }
            finally
            {
                await page.CloseAsync();
            }
        }

        public void Dispose()
        {
            if (!_disposed)
            {
                _httpClient.Dispose();
                _browser.CloseAsync().GetAwaiter().GetResult();
                _playwright.Dispose();
                _disposed = true;
            }
        }
    }
}
