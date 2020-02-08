using System.Threading;
using System.Threading.Tasks;

namespace PluginLoader
{
    public struct TaskTokenPair
    {
        public readonly Task Task;
        public readonly CancellationTokenSource TokenSource;

        public TaskTokenPair(Task task, CancellationTokenSource tokenSource)
        {
            this.Task = task;
            this.TokenSource = tokenSource;
        }
    }
}