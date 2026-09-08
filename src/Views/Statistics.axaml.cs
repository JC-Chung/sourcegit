using System.Linq;
using Avalonia.Controls;
using Avalonia.Interactivity;

namespace SourceGit.Views
{
    public partial class Statistics : ChromelessWindow
    {
        public Statistics()
        {
            CloseOnESC = true;
            InitializeComponent();
        }

        private void OnAuthorSelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (DataContext is ViewModels.Statistics vm && sender is ListBox listBox)
                vm.ChangeAuthor(listBox.SelectedItem as Models.StatisticsAuthor);
        }

        private void OnShowAllAuthors(object sender, RoutedEventArgs e)
        {
            if (sender is Button btn && btn.Parent is Grid grid)
            {
                var listBox = grid.Children.OfType<ListBox>().FirstOrDefault();
                if (listBox != null)
                    listBox.SelectedItem = null;
            }

            if (DataContext is ViewModels.Statistics vm)
                vm.ChangeAuthor(null);
        }
    }
}
