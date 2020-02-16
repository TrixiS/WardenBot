using System;
using System.IO;
using System.Linq;
using System.Threading;
using System.Reflection;
using System.Threading.Tasks;
using System.Collections.Generic;
using WardenAPI.Plugins;

namespace PluginLoader
{
    public class Loader
    {
        public IEnumerable<IPlugin> RegisteredPlugins =>
            this.runningPlugins.Keys.Select(p => p.Plugin);

        private readonly Dictionary<AssemblyPlugin, CancellationTokenSource> runningPlugins;
        private readonly AssemblyLoader assemblyLoader;

        public Loader(AssemblyLoader assemblyLoader)
        {
            this.assemblyLoader = assemblyLoader;
            this.runningPlugins = new Dictionary<AssemblyPlugin, CancellationTokenSource>();
        }

        public void KillPluginExecution(Assembly assembly, Type pluginType = null)
        {
            if (!this.runningPlugins.Any())
                return;

            IEnumerable<AssemblyPlugin> toRemove;
            
            if (pluginType != null)
            {
                toRemove = this.runningPlugins.Keys.Where(p =>
                    p.PluginAssembly == assembly && p.Plugin.GetType() == pluginType);
            }
            else
            {
                toRemove = this.runningPlugins.Keys.Where(p => 
                    p.PluginAssembly == assembly);
            }

            foreach (var plugin in toRemove)
            {
                this.runningPlugins[plugin].Cancel();
                this.runningPlugins.Remove(plugin);
            }
        }

        private void RunPlugin(AssemblyPlugin plugin)
        {
            var tokenSource = new CancellationTokenSource();

            Task.Run(async () =>
            {
                await plugin.Plugin.RunAsync(tokenSource.Token);

                if (this.runningPlugins.ContainsKey(plugin))
                    this.runningPlugins.Remove(plugin);
            });

            this.runningPlugins[plugin] = tokenSource;
        }

        private IEnumerable<AssemblyPlugin> GetPlugins(Assembly assembly)
        {
            var pluginsTypes = assembly.ExportedTypes.Where(t => t.GetInterface(nameof(IPlugin)) != null);

            if (!pluginsTypes.Any())
                return Enumerable.Empty<AssemblyPlugin>();

            List<AssemblyPlugin> plugins = new List<AssemblyPlugin>();

            foreach (Type pluginType in pluginsTypes)
            {
                IPlugin plugin = (IPlugin) Activator.CreateInstance(pluginType);

                plugins.Add(new AssemblyPlugin
                {
                    Plugin = plugin,
                    PluginAssembly = assembly
                });
            }

            return plugins;
        }

        private IEnumerable<AssemblyPlugin> PluginsFromPath(string path)
        {
            Assembly[] assemblies = this.assemblyLoader.LoadAssemblies(
                File.GetAttributes(path).HasFlag(FileAttributes.Directory)
                    ? Directory.GetFiles(path, "*.dll")
                    : new string[] {path});

            if (!assemblies.Any() || assemblies == null)
                throw new Exception($"No plugins found in {path}.");

            List<AssemblyPlugin> plugins = new List<AssemblyPlugin>();

            foreach (Assembly assembly in assemblies)
                plugins.AddRange(this.GetPlugins(assembly));

            return plugins;
        }

        public void RunPluginsFromPath(string path)
        {
            foreach (AssemblyPlugin plugin in this.PluginsFromPath(path))
                this.RunPlugin(plugin);
        }
    }
}