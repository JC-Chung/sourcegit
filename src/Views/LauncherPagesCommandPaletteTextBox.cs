using System;
using System.Collections.Generic;

using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;

namespace SourceGit.Views
{
    public record LauncherPagesCommandPaletteSuggestion(
        TextBox Target,
        string Token,
        string Description,
        int ReplaceLen)
    {
        public void Use()
        {
            var text = Target.Text ?? string.Empty;
            var completed = Token + " ";

            Target.Text = completed + text.Substring(Math.Min(ReplaceLen, text.Length));
            Target.CaretIndex = completed.Length;
        }
    }

    public class LauncherPagesCommandPaletteTextBox : TextBox
    {
        public static readonly DirectProperty<LauncherPagesCommandPaletteTextBox, List<LauncherPagesCommandPaletteSuggestion>> SuggestionsProperty =
            AvaloniaProperty.RegisterDirect<LauncherPagesCommandPaletteTextBox, List<LauncherPagesCommandPaletteSuggestion>>(
                nameof(Suggestions),
                static o => o.Suggestions);

        public List<LauncherPagesCommandPaletteSuggestion> Suggestions
        {
            get => _suggestions;
            set => SetAndRaise(SuggestionsProperty, ref _suggestions, value);
        }

        public static readonly DirectProperty<LauncherPagesCommandPaletteTextBox, int> SelectedSuggestionIndexProperty =
            AvaloniaProperty.RegisterDirect<LauncherPagesCommandPaletteTextBox, int>(
                nameof(SelectedSuggestionIndex),
                static o => o.SelectedSuggestionIndex,
                static (o, v) => o.SelectedSuggestionIndex = v);

        public int SelectedSuggestionIndex
        {
            get => _selectedSuggestionIdx;
            set => SetAndRaise(SelectedSuggestionIndexProperty, ref _selectedSuggestionIdx, value);
        }

        protected override Type StyleKeyOverride => typeof(TextBox);

        protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
        {
            base.OnPropertyChanged(change);

            if (change.Property == TextProperty)
                UpdateSuggestions();
        }

        protected override void OnLostFocus(RoutedEventArgs e)
        {
            base.OnLostFocus(e);
        }

        protected override void OnKeyDown(KeyEventArgs e)
        {
            if (_suggestions != null)
            {
                if (e.Key == Key.Up)
                {
                    SelectedSuggestionIndex = _selectedSuggestionIdx > 0
                        ? _selectedSuggestionIdx - 1
                        : _suggestions.Count - 1;
                    e.Handled = true;
                }
                else if (e.Key == Key.Down)
                {
                    SelectedSuggestionIndex = _selectedSuggestionIdx < _suggestions.Count - 1
                        ? _selectedSuggestionIdx + 1
                        : 0;
                    e.Handled = true;
                }
                else if (e.Key == Key.Enter || e.Key == Key.Tab)
                {
                    _suggestions[_selectedSuggestionIdx].Use();
                    e.Handled = true;
                }
                else if (e.Key == Key.Escape)
                {
                    Suggestions = null;
                    e.Handled = true;
                }
            }

            if (!e.Handled)
                base.OnKeyDown(e);
        }

        private void UpdateSuggestions()
        {
            var text = Text ?? string.Empty;

            if (string.IsNullOrEmpty(text) || text.Contains(' '))
            {
                Suggestions = null;
                return;
            }

            var matches = new List<LauncherPagesCommandPaletteSuggestion>();
            foreach (var (token, textKey) in s_filters)
            {
                if (token.StartsWith(text, StringComparison.OrdinalIgnoreCase) &&
                    !token.Equals(text, StringComparison.Ordinal))
                    matches.Add(new(this, token, App.Text(textKey), text.Length));
            }

            if (matches.Count > 0)
            {
                Suggestions = matches;
                SelectedSuggestionIndex = 0;
            }
            else
            {
                Suggestions = null;
            }
        }

        private static readonly (string Token, string TextKey)[] s_filters =
        [
            ("is:tracking", "LauncherPagesCommandPalette.Filter.Tracking"),
            ("is:ahead",    "LauncherPagesCommandPalette.Filter.Ahead"),
            ("is:behind",   "LauncherPagesCommandPalette.Filter.Behind"),
            ("is:dirty",    "LauncherPagesCommandPalette.Filter.Dirty"),
        ];

        private List<LauncherPagesCommandPaletteSuggestion> _suggestions = null;
        private int _selectedSuggestionIdx = 0;
    }
}
