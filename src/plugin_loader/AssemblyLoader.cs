using System;
using System.Reflection;

namespace PluginLoader
{
    public class AssemblyLoader
    {
        public Assembly[] LoadAssemblies(params string[] paths)
        {   
            var assemblies = new Assembly[paths.Length];

            for (int i = 0; i < paths.Length; i++)
            {
                try
                {
                    assemblies[i] = Assembly.LoadFile(paths[i]);
                }
                catch 
                { 
                    continue;
                }
            }

            return assemblies;
        }
    }
}