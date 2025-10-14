using Allure.Commons;
using Microsoft.Playwright.NUnit;
using NUnit.Allure.Attributes;
using NUnit.Allure.Core;
using NUnit.Framework;
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

// Page Object Model for Wikipedia Playwright page
public class WikiPage
{
    private readonly IPage _page;

    public WikiPage(IPage page)
    {
        _page = page;
    }

    // XPath locator for Debugging features section
    public ILocator DebuggingSection => _page.Locator("//h2[contains(.,'Debugging features')]//following-sibling::p | //h2[contains(.,'Debugging features')]//following-sibling::ul");

    // Locator for Microsoft development tools section
    public ILocator TechSection => _page.Locator("#Microsoft_development_tools");

    // Locator for technology links
    public ILocator TechLinks => TechSection.Locator("a");

    // XPath locator for Appearance dropdown
    public ILocator Appearance => _page.Locator("//div[contains(@class,'vector-appearance-dropdown')]");

    // Locator for Dark mode
    public ILocator DarkMode => _page.Locator("[data-mw-skin='vector-night-mode']");

    // Get text from Debugging features section
    public async Task<string> GetDebuggingTextAsync()
    {
        var texts = await DebuggingSection.AllInnerTextsAsync();
        return string.Join(" ", texts);
    }

    // Check if all technologies are links
    public async Task<bool> AreTechLinksAsync()
    {
        var links = await TechLinks.AllAsync();
        foreach (var link in links)
        {
            if (string.IsNullOrEmpty(await link.GetAttributeAsync("href")))
                return false;
        }
        return true;
    }

    // Switch to Dark mode
    public async Task SwitchToDarkAsync()
    {
        await Appearance.ClickAsync();
        await DarkMode.ClickAsync();
    }

    // Check if Dark mode is active
    public async Task<bool> IsDarkModeAsync()
    {
        var bodyClass = await _page.EvalOnSelectorAsync<string>("body", "el => el.className");
        return bodyClass.Contains("skin-theme-clientpref-night");
    }
}

// Utility for normalizing text and counting words
public static class TextNormalizer
{
    // Normalize text: remove HTML, punctuation, extra spaces, lowercase
    public static string Normalize(string text)
    {
        text = Regex.Replace(text, @"<[^>]+>", ""); // Strip HTML tags
        text = Regex.Replace(text, @"\s+", " "); // Replace multiple spaces with one
        text = text.ToLowerInvariant().Trim(); // Lowercase and trim
        text = Regex.Replace(text, @"[^\w\s]", ""); // Remove punctuation
        return text;
    }

    // Count unique words in text
    public static int CountUniqueWords(string text)
    {
        var words = text.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var uniqueWords = new HashSet<string>(words);
        return uniqueWords.Count;
    }
}

// Test class for Wikipedia tasks
[AllureNUnit]
public class WikiTests : PageTest
{
    private const string Url = "https://en.wikipedia.org/wiki/Playwright_(software)";
    private WikiPage _wikiPage;
    private HttpClient _httpClient;

    [SetUp]
    public async Task Setup()
    {
        _httpClient = new HttpClient();
        await Page.GotoAsync(Url);
        _wikiPage = new WikiPage(Page);
    }

    // Task 1: Compare unique words from UI and API
    [Test, AllureTag("Task1")]
    public async Task CompareDebuggingWords()
    {
        // Get text from UI
        var uiText = await _wikiPage.GetDebuggingTextAsync();
        var normUiText = TextNormalizer.Normalize(uiText);
        var uiWordCount = TextNormalizer.CountUniqueWords(normUiText);

        // Get section number for Debugging features
        var sectionUrl = "https://en.wikipedia.org/w/api.php?action=parse&page=Playwright_(software)&prop=sections&format=json";
        var sectionJson = await _httpClient.GetStringAsync(sectionUrl);
        var sectionData = JsonSerializer.Deserialize<WikiSectionsResponse>(sectionJson);
        var section = sectionData.Parse.Sections.FirstOrDefault(s => s.Line == "Debugging features");
        Assert.IsNotNull(section, "Debugging features section not found");

        // Get text from API
        var apiUrl = $"https://en.wikipedia.org/w/api.php?action=parse&page=Playwright_(software)&section={section.Index}&prop=text&format=json";
        var apiJson = await _httpClient.GetStringAsync(apiUrl);
        var apiData = JsonSerializer.Deserialize<WikiParseResponse>(apiJson);
        var apiText = apiData.Parse.Text["*"];
        var normApiText = TextNormalizer.Normalize(apiText);
        var apiWordCount = TextNormalizer.CountUniqueWords(normApiText);

        // Compare word counts
        Assert.AreEqual(uiWordCount, apiWordCount, "Unique word counts do not match");
    }

    // Task 2: Validate all technology names are links
    [Test, AllureTag("Task2")]
    public async Task ValidateTechLinks()
    {
        var areLinks = await _wikiPage.AreTechLinksAsync();
        Assert.IsTrue(areLinks, "Not all technology names are links");
    }

    // Task 3: Switch to Dark mode and verify
    [Test, AllureTag("Task3")]
    public async Task SwitchAndVerifyDarkMode()
    {
        await _wikiPage.SwitchToDarkAsync();
        var isDark = await _wikiPage.IsDarkModeAsync();
        Assert.IsTrue(isDark, "Dark mode was not applied");
    }
}

// API response models
public class WikiParseResponse
{
    public Parse Parse { get; set; }
}

public class Parse
{
    public string Title { get; set; }
    public Dictionary<string, string> Text { get; set; }
}

public class WikiSectionsResponse
{
    public ParseSections Parse { get; set; }
}

public class ParseSections
{
    public List<Section> Sections { get; set; }
}

public class Section
{
    public int Index { get; set; }
    public string Line { get; set; }
}